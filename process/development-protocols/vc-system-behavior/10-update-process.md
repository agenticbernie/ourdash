---
name: protocol:vc-system-behavior-10-update-process
description: "UPDATE PROCESS phase reference: closeout packet, Tier-1 required audits, and archival."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 1
  required: false
  read_when: "running or auditing the UPDATE PROCESS phase"
---

# UPDATE PROCESS Phase

The UPDATE PROCESS phase archives completed work, updates project knowledge, and closes out the session cleanly.

---

## Agent and Tools

**Agent:** `vc-update-process-agent`
**Tools:** Read, Write, Edit, Grep, Glob, Bash
**Entry point:** User says `ENTER UPDATE PROCESS MODE` after EVL confirms all gates are green (under /goal: auto-entered on EVL completion, no user command).

---

## Session Start — 5 Required Skills (Tier 0)

Run all 5 before doing any archival work. No exceptions.

> **Single-trip rule (PHASE-GATES).** UPDATE PROCESS has exactly two user touchpoints: an **entry** Combined Clarification Gate (the `ENTER UPDATE PROCESS MODE` trigger + this restatement, in one round-trip — the Tier-0 skills below run as silent prep, not a second pause) and an **exit** terminal Phase-End Recommendation Gate (move-on / start-new-program / loop-back). Phase-3 improvement approvals ride inside the exit gate, not as a separate mid-phase pause. Under `/goal` both gates auto-proceed. See `12-reference.md` PHASE-GATES.

**[U-S0] vc-intent-clarify** — REQUIRED FIRST. Restate the scope of what is being updated and archived. Do **NOT** add a separate confirmation pause — the restatement rides on the `ENTER UPDATE PROCESS MODE` entry trigger as the single entry gate.

**[U-S1] vc-context-discovery** — REQUIRED. Load context for this update pass (Part A + B frontmatter).

**[U-S2] vc-plan-discovery** — REQUIRED. Run alongside U-S1.

**[U-S3] vc-review-situation** — REQUIRED. Check branch, worktrees, and in-flight work before making archival decisions.

**[U-S4] vc-agent-strategy-compare** — REQUIRED. Decide the strategy for this update-process pass.

**Pre-acceptance check [U-S5-pre]:** Before accepting the EVL handoff, check that the file at `preliminary_packet_path:` (from the EVL HANDOFF SUMMARY block) exists on disk. If it does not exist, ask the orchestrator to re-run EVL steps 1-3 from scratch. (This is a machine-to-machine re-run request between update-process-agent and the orchestrator, not a user pause — under /goal it happens automatically.)

**[U-S5] vc-generate-closeout** — REQUIRED. Run this before archiving any plan or updating umbrella state. It produces the 9-field closeout packet.

---

## Required Skills — Phase 3 (run after auditing what changed)

**[U1] vc-audit-vc** — REQUIRED if any agent, skill, or `.claude/` file was modified.

Runs:
- `validate-agent-parity.mjs`
- `validate-skills.mjs`
- `validate-guide-sync.mjs`
- `validate-protocol-wiring.mjs`
- `validate-seeds.mjs`
- `validate-kit-portability.mjs`

**[U2] vc-audit-context** — REQUIRED if any `process/context/` file or context group was modified. Also REQUIRED if the EVL handoff summary contains any `CONTEXT_PARTIAL: [area]` flags — even if no context file was directly modified.

Runs:
- `validate-context-discovery.mjs`
- `validate-all-context.mjs`

**CONTEXT_PARTIAL de-duplication:** If the same area was already audited in a prior phase and the audit found "gap unresolvable — no context doc exists": skip re-auditing that area. Record: "context gap noted in phase [N]; no new audit needed."

**[U3] vc-audit-plans** — REQUIRED at natural stopping points (feature complete or "what's next?").

Runs:
- `validate-plan-inventory.mjs`

Surfaces stale, missing, or mis-classified plans before declaring the session complete.

---

## Required Validators

Run these after any agent, skill, or protocol change. You may not claim the update is complete until you report these results or explain exactly why one was intentionally skipped.

```bash
node .claude/skills/vc-audit-vc/scripts/validate-agent-parity.mjs
node .claude/skills/vc-audit-context/scripts/validate-context-discovery.mjs
node .claude/skills/vc-audit-vc/scripts/validate-skills.mjs
git diff --check
node .claude/skills/vc-audit-vc/scripts/validate-guide-sync.mjs
node .claude/skills/vc-audit-vc/scripts/validate-kit-portability.mjs
```

If context grouping changed:

```bash
node .claude/skills/vc-generate-context/scripts/validate-all-context.mjs
```

If plan inventory changed:

```bash
node .claude/skills/vc-audit-plans/scripts/validate-plan-inventory.mjs
```

If a phase program completed or umbrella state changed:

```bash
node .claude/skills/vc-audit-plans/scripts/validate-umbrella-state.mjs
node .claude/skills/vc-audit-plans/scripts/validate-phase-reports.mjs
node .claude/skills/vc-audit-plans/scripts/validate-backlog-notes.mjs
```

> Run these when a phase program completed or umbrella state changed. Skip any that does not apply to the current change (e.g. backlog-notes runs only when a phase program completed) and record the skip reason.

---

## Closeout Packet — 9 Required Fields

The `vc-generate-closeout` skill produces this packet. All 9 fields are required. Emit it as a fenced block in the session chat before any archival action. Also write it to the phase report under `## Closeout Packet`.

1. **Selected plan path** — exact file path (never implicit)
2. **Closeout classification** — exactly one of:
   - `"Ready for UPDATE PROCESS archival"`
   - `"Keep in active/ — needs further testing"`
   - `"Needs PLAN/UPDATE PROCESS reconciliation"`
   - **Hard E2E gate (all developed behavior).** Any developed behavior (backend, container, browser, or frontend) CANNOT be classified `"Ready for UPDATE PROCESS archival"` without a passing fully-automated E2E/integration test proving it, wherever the surface is automatable. If a developed-behavior criterion lacks a passing E2E gate, classify the plan `"Keep in active/ — needs further testing"` and create a test-building backlog stub (Step 5) for the missing E2E coverage. An agent-probe or documented known-gap does not satisfy this gate. This is a classification constraint, not a /goal stop: **under /goal**, a missing E2E gate auto-creates the test-building backlog stub and continues — never a live block.
3. **What was finished** — what actually happened (not a restatement of the plan)
4. **What was verified vs still unverified** — test evidence vs pending verification
   - **4b. Validate-contract compliance** — present and its state, OR a documented skip reason. A plan cannot be classified "Ready for archival" without one of these.
   - **Recovery path when absent:** If the validate-contract is absent and no skip reason was documented, classify the plan as "Keep in active/ — needs further testing" — not "Ready for archival". Write a backlog note: "missing validate-contract — plan needs PVL before archival." Do not route back to vc-validate-agent. This is a classification constraint, not a blocker.
5. **Cleanup done vs still needed** — updated docs and reports vs open TODOs
6. **Single best next valid state** — the exact next action or plan path (never generic)
7. **Commit-checkpoint recommendation** — invoke vc-git-manager now or after UPDATE PROCESS?
8. **Regression status** (phase programs only) — previously verified surfaces checked, plus outcome
9. **SPEC achievement** — each SPEC acceptance criterion scored against its named `proven by:` test scenario/gate: `met (passing test: [scenario/gate])` or `unmet → backlog` (with backlog-note path). The proof must be the specific test scenario/gate that proves the criterion, not a general claim of completion. **Any criterion covering developed behavior scored `met` REQUIRES a passing fully-automated E2E/integration gate as the proof wherever the surface is automatable** — an agent-probe result or a documented known-gap is NOT sufficient proof for a developed-behavior criterion; such a criterion stays `unmet → backlog` until the E2E gate passes. Mirrors the phase report's `## SPEC Achievement` heading.

### Double Invocation Rule

`vc-generate-closeout` fires at two points:

1. **EVL Step 1** — produces the preliminary closeout packet
2. **UPDATE PROCESS U-S5** — produces the authoritative closeout packet

The U-S5 packet always supersedes the EVL preliminary packet.

- Same session: U-S5 may use the EVL packet as a starting point and update only changed fields.
- Different session (crash recovery): U-S5 runs fresh. The EVL packet is preliminary only.

**EVL preliminary packet disk write.** EVL step 1 must write the preliminary closeout packet to disk before routing to UPDATE PROCESS. This file is the crash-recovery source. If it is absent, U-S5 re-runs EVL gate checks from scratch.

Write path:
- Feature-scoped: `process/features/{feature}/reports/{phase}-evl-preliminary.md`
- General plans: `process/general-plans/reports/{phase-slug}-evl-preliminary.md`

Where `{phase}` = plan filename slug (strip `_PLAN_*.md` suffix) for non-phase-program work (example: if plan file is `myfeature_PLAN_06-06-26.md` → slug is `myfeature`); for phase programs = `phase-N` (zero-padded, e.g. `phase-01`). `{feature}` = feature folder name (e.g. `billing`, `connections`).

---

## Drift Signal Scoring

Count signals from these 5 sources. Use the exact threshold phrases below — do not paraphrase.

**Signal sources:**
- **(a)** Files touched: 1–4 files = 0 signal; 5+ files = 1 signal
- **(b1)** `process/development-protocols/`, `.claude/agents/`, or `.claude/skills/` changed = 1 signal
- **(b2)** `README.md`, `AGENTS.md`, or `CLAUDE.md` changed = 1 additional signal (max 2 from b)
- **(c)** 3 or more memory-worthy observations = 1 signal. Memory-worthy means: user corrected agent behavior, a known gap was found, a new pattern was established, or a feedback-like observation was made.
- **(d)** New feature folder created or deleted = 1 signal
- **(e)** Validate-contract written or overwritten = 1 signal

Maximum possible score: 6

**Threshold phrases (use verbatim):**
- **LOW (0–1):** `"UPDATE PROCESS available if you want."`
- **MEDIUM (2):** `"Recommend UPDATE PROCESS -- significant changes detected."`
- **HIGH (3+):** `"Strongly recommend UPDATE PROCESS -- harness/protocol files touched."`

**Under /goal:** Drift scoring is informational only. It populates the phase report but does not produce a recommendation phrase (the agent is already in UPDATE PROCESS). If drift is 3 or higher, automatically create follow-up plan stubs for gap items. Do not spawn vc-execute-agent autonomously without PVL validation — that would bypass inner loop gates. Archive the current plan; the follow-up stub is the forward path.

### Drift Escalation

- Drift 1–2 → backlog entry.
- Drift 3+ → create a follow-up plan stub for the gap items. Under /goal: satisfy via auto-stub creation (do NOT spawn vc-execute-agent without PVL); archival proceeds — never a live block.

---

## 7-Step Archival Checklist

Run these steps in order for every completed phase before archiving.

1. **Update the plan file.** Mark completed checklist items. Record any deviations from the plan. Tick the Step 7 checkbox in `## Phase Loop Progress`: `- [x] 7. UPDATE PROCESS — archived; context updated; committed`. Do not modify the `## Validate Contract` section — that is owned by vc-validate-agent. If a validate-contract update is needed (e.g., correcting the `supersedes:` field): spawn vc-validate-agent in contract-update mode.

2. **Write the phase report** to `process/features/{feature}/reports/` or `process/general-plans/reports/`. See the Phase Report Format section below for required headings.

3. **Update the umbrella plan's `## Current Execution State`** (phase programs only). Rewrite this section — do not append to it. Run `validate-umbrella-state.mjs` after updating.

4. **Move the plan file.** Move from `active/` to `completed/` if classified "Ready for archival". Leave in `active/` if classified "Keep in active/ — needs further testing". Any developed behavior without a passing fully-automated E2E/integration gate — wherever the surface is automatable — is NOT archivable; keep it in `active/` (needs further testing) and write a test-building backlog stub (Step 5) for the missing E2E coverage. Under /goal this auto-stub is created and the phase continues; it is never a live block.

5. **Write backlog notes** for any gap that could not be resolved. Write a NOTE file to `backlog/` with name, description, severity, effort, and group metadata. Do not silently drop gaps. Run `validate-backlog-notes.mjs` (not built yet; runs only when a phase program completed — skip otherwise).
   - EVL-originated backlog notes: verify that the paths from the EVL HANDOFF SUMMARY exist on disk. Then add any phase-level gaps not already covered by EVL. Do not duplicate EVL backlog notes.

6. **Update context files.** If durable project knowledge changed: update the smallest relevant context file, update the owning `all-{group}.md`, and update `all-context.md` if routing changed.

7. **Write memory entries.** If there are user feedback, project, or reference learnings, write them to the memory directory with the correct type. Scan `MEMORY.md` for entries that have matured into stable patterns worth promoting. Keep index entries concise so the index stays within its size budget; do not silently truncate entries.

---

## Phase Report Format

Required YAML frontmatter:

```yaml
---
phase: [phase-name-slug]
date: [YYYY-MM-DD]
status: [COMPLETE | COMPLETE_WITH_GAPS | BLOCKED]
feature: [feature-folder-name]
plan: [path/to/plan-file.md]
---
```

### 9 Required Headings

These heading names are canonical. Do not rename them. All must appear in every phase report, even if a section is brief.

- `## What Was Done`
- `## What Was Skipped or Deferred`
- `## Test Gate Outcomes`
- `## Plan Deviations`
- `## Test Infra Gaps Found`
- `## SPEC Achievement`
- `## SPEC Gaps`
- `## Closeout Packet`
- `## Forward Preview`

**`## SPEC Achievement` (required).** Score the delivered work against the upstream SPEC's acceptance criteria. List each SPEC acceptance criterion with a verdict scored against its named `proven by:` test scenario/gate: `met (passing test: [scenario/gate])` or `unmet → backlog`. The proof for `met` must be the specific test scenario/gate that proves the criterion. **Any criterion covering developed behavior requires a passing fully-automated E2E/integration gate as the proof wherever the surface is automatable** — an agent-probe or a known-gap is not sufficient; a developed-behavior criterion without a passing E2E gate stays `unmet → backlog`. For every `unmet` criterion, write a backlog note (Step 5 of the Archival Checklist) and reference its path here. This is UPDATE PROCESS's authoritative scoring of whether the session delivered what the SPEC required.

### Forward Preview — 4 Required Subsections

Write the Forward Preview for the next phase's agent, not as a historical record. All 4 subsections are required even if brief.

```
## Forward Preview

### Test Infra Found
[Test infra improvements discovered this phase — gaps, new helpers, missing runners, slow tests worth fixing]

### Blast Radius Changes
[Any blast-radius surface that changed from what the outer-loop plan specified. For Phase 1: compare against the outer-loop plan blast-radius and list any expansions or contractions. If unchanged: write explicitly: "no changes from outer-loop plan." For standalone plans: compare against the plan's own ## Blast Radius section as written at PLAN time. List any files added, removed, or changed during EXECUTE that were not in the original blast-radius listing. If no deviations: write "No blast-radius deviations — all changes were within planned scope."]

### Commands to Stay Green
[Test commands from this phase's validate-contract that must remain green in subsequent phases — copy exact commands]

### Dependency Changes
[Outputs this phase produces that downstream phases depend on — file paths, API contracts, schema state, env vars added]
```

**Reading strategy for later phases:** Read the immediately prior phase report in full. For all earlier phases, read only the `## Forward Preview` section. See Section 8 Step 0 for the boundary definition (Phase N-1 = full read; Phase N-2+ = Forward Preview only).

---

## User Input

UPDATE PROCESS has exactly two user touchpoints — one at entry, one at exit. No mid-phase pauses.

- **Entry:** type `ENTER UPDATE PROCESS MODE` (carries the U-S0 restatement) — the single entry gate.
- **Exit:** the terminal Phase-End Recommendation Gate (see Exit Gate). Phase-3 improvement approvals are **not** a separate mid-phase pause — the proposed improvements (numbered list) are presented as part of this single exit gate, answered once: `"1. yes 2. no 3. yes"` (one answer per item).
- **Mid-phase:** none.
- **Under /goal:** both gates auto-proceed; all improvements within blast radius are applied automatically without asking.

---

## Terminal Phase-End Recommendation Gate (single round-trip)

UPDATE PROCESS is the terminal phase, so its exit gate recommends what the session does *next* — there is no fixed downstream phase. Present everything in one block for **confirm / push back / go**, with the recommended option driven by the drift score:

1. **Closeout summary** — closeout packet classification + drift score + what was archived/updated + any Phase-3 improvements proposed (numbered, for one-shot approval).
2. **Recommended next step (marked recommended), bidirectional** — driven by drift:
   - **Move on / close out** (recommended when drift is LOW 0–1) — session complete; `"UPDATE PROCESS complete. Ready for next feature or task."`
   - **Start a new phase program** (recommended when natural next work was identified) — route through `vc-generate-phase-program` to scaffold the umbrella + stubs.
   - **Loop back on drift** (recommended when drift is HIGH 3+ and gap items remain) — create follow-up plan stubs / re-open targeted work. Bounded by the vc-autoresearch 10-cycle cap. Under /goal: auto-create stubs (per Drift Signal Scoring); do NOT spawn vc-execute-agent without PVL.
3. **Optional deep work** (extra audit pass, memory consolidation, plan-inventory cleanup) offered as *choices*, not a pause.

Under `/goal` this gate auto-proceeds on the drift-driven recommended option.

---

## Exit Gate (machine checklist)

All of these must be true before the phase is complete:

- [U-S1] vc-context-discovery ran
- [U-S2] vc-plan-discovery ran
- Context and protocol docs updated as applicable
- All validators run and results reported
- Phase report written (includes test infra gaps)
- Backlog notes written for all unresolved gaps
- User responded at the terminal Phase-End Recommendation Gate (interactive); or auto-proceeded (under /goal)
- Emit: `"UPDATE PROCESS complete. Ready for next feature or task."`

Under /goal: emit `PHASE_COMPLETE: UPDATE PROCESS — [phase name] archived; phase report written; process commit invoked. Proceed to next phase Step 0.`

The orchestrator matches on the prefix `PHASE_COMPLETE: UPDATE PROCESS` — the suffix is informational and not strictly parsed.

**Artifacts produced:** archived plan, phase report, context updates, memory entries, backlog notes.
