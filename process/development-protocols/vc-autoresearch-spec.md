---
name: protocol:vc-autoresearch-spec
description: "Deeper design reference for the vc-autoresearch loop primitive (PVL/EVL bookkeeper); SKILL.md is the operative contract."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 7
  required: false
  read_when: "designing or deeply understanding the autoresearch gap-loop primitive used by PVL/EVL"
---

> **STATUS: ACTIVE**
>
> vc-autoresearch is the live loop primitive for the RIPER-5 system. It is the shared
> bookkeeper for PVL (plan-validate-fix loop) and EVL (execute-validate-fix loop), and is
> directly invocable for standalone spec/doc/UX/test hardening.
>
> **Authority:** `.claude/skills/vc-autoresearch/SKILL.md` is the operative contract; this
> document is the deeper design reference. Where the two diverge, the SKILL.md wins.

# vc-autoresearch — Specification

**Version:** 1.0
**Last updated:** 2026-06-08
**Status:** ACTIVE

---

## The idea in one sentence

Find gaps → fix them → repeat until no gaps remain. Extract this loop into a reusable skill so PVL, EVL, and standalone quality runs all share the same mechanics.

---

## The loop shape (all three use this)

```
START
  │
  ▼
Research step — find gaps in the corpus
  │
  ├─ Zero gaps found? ──► STOP (success)
  │
  ▼
Write iteration report (what was found, what was fixed)
  │
  ▼
Fix step — apply all gap resolutions
  │
  ▼
Optional safety check — did we break anything?
  │
  ├─ Safety check failed? ──► revert fixes, try again
  │
  ▼
Termination check — should we stop?
  │
  ├─ Yes (cap reached, plateau, etc.) ──► STOP
  │
  └─ No ──► back to Research step
```

All three loops in the vc-system follow this shape:

| | What we ran (I1–I11) | PVL | EVL |
|---|---|---|---|
| **Corpus** | spec .md files + agent files | plan .md file | changed source + test files |
| **Research step** | 2 parallel agents scan for behavioral gaps | vc-validate-agent runs V1-V7 gates | vc-tester runs validate-contract gate commands |
| **Gap signal** | agents list findings with severity | FAIL / CONDITIONAL / CONCERN | failing gate command (non-zero exit) |
| **Fix step** | 3 parallel agents edit the files | vc-plan-agent supplements the plan | vc-execute-agent fixes failing code (supplement mode) |
| **How we know done** | until agents find no gaps | validate-agent returns PASS | hit the metric goal |
| **"Done" signal** | all agents ALL_CLEAR for 2 consecutive iterations | PASS (or CONDITIONAL accepted after 10-cycle cap) | all validate-contract fully-automated gates pass |
| **Commands** | configured per invocation | V1-V7 gate sequence (vc-validate-agent owns) | exact commands from validate-contract "Test gates" field — never invented |
| **Iteration cap** | 15 (spec domain default) | 10 validate-fix loops | 10 execute-validate-fix loops |
| **Logs** | .md report + TSV per iteration | not formally logged | EVL HANDOFF SUMMARY + preliminary closeout packet |

The domain-specific details (which agents run, what the gates check, how supplementing works) stay where they are. vc-autoresearch provides the loop mechanics: iteration counter, convergence detection, iteration reports, plateau detection.

---

## Two ways to know when you're done

### Until agents find no gaps

Used when there is no number to measure. The loop runs until research agents find nothing worth fixing.

**When to use:** spec hardening, doc completeness, UX consistency, plan quality pre-PVL.

**How it stops:** agents return `ALL_CLEAR` — all investigation threads found nothing above the severity floor. When all agents return `ALL_CLEAR` for K consecutive iterations, the loop stops.

**Example:** the I1–I11 behavior gap analysis. Two agents scanned the spec files. The loop would stop when both reported zero actionable gaps.

### Hit the metric goal

Used when the goal is a number. The loop runs a test or script after each fix batch and checks the output against a target.

**When to use:** test coverage %, lint error count, type error count, bundle size.

**How it stops:** run the verify script, read its output. When the number hits the target (or the loop plateaus), the loop stops.

**Example:** EVL. Run `pnpm test`, count failing tests. Stop when failing count is zero.

Both use the same loop shape. The only difference is what "done" means.

---

## Goal Block Integration During Loops

When vc-autoresearch runs a plan-validate-fix or execute-validate-fix loop in an autopilot session:

1. **Check for goal file:** Before loop starts, check if `{slug}_AUTOPILOT_GOAL_*.md` exists in task folder.

2. **If goal file exists (autopilot run active):**
   - Read the goal block's `DECISION POLICY` field (the policy for gap handling).
   - Emit per-cycle iteration reports: `{plan-slug}-{domain}-iteration-{NNN}_REPORT_{dd-mm-yy}.md`
     - Domain: `pvl` for plan-validate-fix, `evl` for execute-validate-fix
     - NNN: 3-digit cycle counter (001, 002, ..., 010)
   - Each iteration report includes:
     - Cycle number
     - Gap count (before/after)
     - Plan sections modified
     - Test gate pass/fail summary
     - Policy decision applied (auto-supplement, accept CONDITIONAL, etc.)
   - At final cycle (10 or success): append `## Autoresearch Loop Summary [YYYY-MM-DD]` to the goal block file with: cycle count, final verdict, known-gaps accepted.

3. **If goal file does NOT exist (non-autopilot run):**
   - Continue loop as-is. No goal block interaction.

---

## What the skill owns vs what stays in the phase agents

**vc-autoresearch owns:**
- Iteration counter (how many times have we looped)
- Convergence check (are we done? — by verdict or metric)
- Plateau detection (gap count not improving for N iterations → stop)
- Severity floor escalation (after many iterations, ignore minor findings)
- Iteration report writing (.md per iteration + TSV row)
- Regression detection (did a fix introduce new gaps in previously-clear areas)

**Phase agents keep their own mechanics:**
- PVL: V1-V7 gate sequence, SUPPLEMENT REQUEST format, validate-contract write, known-gap exclusion, supersedes: logic → stays in vc-validate-agent and vc-plan-agent
- EVL: which gate commands to run, execute-supplement scoping, HANDOFF SUMMARY format, agent-probe re-invocation → stays in vc-tester and vc-execute-agent
- Spec iterations: which investigation threads to run, which files to assign to which agent → configured per invocation

The skill is a loop bookkeeper, not a framework that replaces phase agent logic.

---

## Termination conditions

Checked after every research pass, in priority order:

```
1. SUCCESS    — agents ALL_CLEAR for K consecutive iterations (verdict)
               OR verify command hits target value (metric)
2. PLATEAU    — gap count unchanged or increased for 3 consecutive iterations
3. SEVERITY   — after N iterations, auto-escalate floor to FAIL-only
               (ignore CONCERNs, keep looping only for FAILs)
4. CAP        — iteration count >= max_iterations
5. REGRESSION — more than 2 regression flags in one iteration → pause for user
```

**Plateau** is the key mechanism for qualitative domains where no scalar target exists. If agents keep finding the same number of gaps without improvement, the loop stops rather than running forever.

**Severity escalation** prevents the loop from running indefinitely on marginal findings. After 7 iterations (default), CONCERN-severity findings are moved to backlog and the loop only continues for FAILs.

---

## When to invoke

vc-autoresearch is invoked directly — no RIPER-5 plan or validate-contract required.

| Situation | Invoke as | Notes |
|---|---|---|
| Iteratively improve a spec/doc | `domain: spec` | What we ran for I1–I11 — until agents find no gaps |
| Add test coverage to a package | `domain: tests`, `verify: pnpm test --coverage` | Hit the metric goal — coverage target |
| Fix all lint/type errors | `domain: errors`, `verify: pnpm typecheck` | Hit the metric goal — zero errors |
| Improve UI component consistency | `domain: ux` | Agents find nothing |
| Refresh stale context docs | `domain: docs` | Agents find nothing |
| Quick plan quality check before PVL | `domain: plan` | 1–3 iterations max |

**PVL kickoff prompt (when not under /goal):** At the start of a PVL-backed autoresearch run, the skill prompts once: "Auto-run (no pauses between cycles) or confirm before each fix batch?" The choice is sticky for the full loop. Under `/goal`, always auto — no prompts.

Under `/goal` generally: all termination conditions auto-accepted except regression budget (more than 2 regression flags in one iteration — pauses for user review).

---

## Canonical domain configs

These are reusable starting configurations. All fields can be overridden per invocation.

### spec
- **Corpus:** `process/development-protocols/*.md`, `.claude/agents/*.md`
- **Investigation threads (per agent):** cross-file signal consistency, undefined cycle caps, missing fallback cases, contradictions, PVL/EVL gate omissions, signal vocabulary gaps
- **Research agents:** 2 (split: behavior-reference + orchestration | agent .md files)
- **Fix agents:** 3 (one per file group)
- **Safety check:** none (structural read-back only)
- **Max iterations:** 15 | Severity escalation at: 7 | Consecutive ALL_CLEAR needed: 2

### tests
- **Corpus:** source files in blast-radius + existing test files
- **Investigation threads:** uncovered public functions, untested error paths, missing edge cases, missing integration tests
- **Verify command:** `pnpm test --coverage` (loop stops when coverage hits metric goal)
- **Safety check:** `pnpm test` (all current tests must still pass after fixes)
- **Max iterations:** 20 | Consecutive clear needed: 1

### ux
- **Corpus:** component files + design token files
- **Investigation threads:** hardcoded colors, missing semantic tokens, missing states (hover/focus/disabled), white/[opacity] anti-patterns, inconsistent spacing
- **Research agents:** 2 (split by component subtree)
- **Safety check:** `pnpm typecheck`
- **Max iterations:** 10 | Severity escalation at: 5 | Consecutive ALL_CLEAR needed: 2

### docs
- **Corpus:** `process/context/**/*.md`
- **Investigation threads:** stale file references, missing routing entries, broken cross-links, outdated procedures, orphaned files
- **Safety check:** `node .claude/skills/vc-audit-context/scripts/validate-context-discovery.mjs`
- **Max iterations:** 8 | Consecutive ALL_CLEAR needed: 1

### plan (lightweight pre-PVL pass)
- **Corpus:** the plan .md file
- **Investigation threads:** missing verification evidence, blast-radius gaps, undefined rollback, incomplete touchpoint list
- **Research agents:** 1 | **Fix agents:** 1
- **Max iterations:** 3 (this is a quick quality pass, not a substitute for PVL)

---

## Iteration report

Written per iteration to: `process/features/{feature}/active/{task-slug}_{dd-mm-yy}/{task-slug}-iteration-{NNN}_REPORT_{dd-mm-yy}.md`

Where `{task-slug}` is the autoresearch run identifier (e.g. `autoresearch-spec-250608`) and `{NNN}` is the zero-padded 3-digit iteration number (`001`, `002`, … `042`). ONE NEW FILE PER ITERATION — never overwrite or append to a previous iteration's report, and never keep a single rolling notes file (no `ITERATION-NOTES.md`). The iteration number appears in BOTH the filename and the frontmatter (`iteration: N`); the cross-iteration rolling view is `results.tsv` only. PVL/EVL cycles use the `{plan-slug}-pvl-iteration-{NNN}` / `{plan-slug}-evl-iteration-{NNN}` slug variants.

### Frontmatter (machine-readable)

```yaml
---
domain: spec | tests | ux | docs | plan | errors
iteration: N
date: YYYY-MM-DD
gaps_found: N
fail_count: N
concern_count: N
applied_count: N
backlogged_count: N
all_clear: true | false
consecutive_all_clear: K
saturation_status: ACTIVE | PLATEAU | SATURATED
new_gaps: N          # compared to previous iteration — used for plateau detection
loop_status: CONTINUE | HALTED_SUCCESS | HALTED_PLATEAU | HALTED_SEVERITY | HALTED_CAP | HALTED_REGRESSION
---
```

### Body sections (human-readable)

- **Summary** — total gaps, severity breakdown, auto-accepted under /goal yes/no
- **Research Agent Findings** — one sub-section per agent, each gap as a structured entry
- **Regression Flags** — any section that had new gaps where previous iteration was ALL_CLEAR
- **Files Updated** — every file touched, with which gap IDs motivated the change
- **Saturation Signal** — new gaps vs previous iteration, plateau assessment, stop recommendation
- **Next Iteration** — thread list carried forward, threads retired (2+ consecutive ALL_CLEAR)

### Gap entry format

```
### GAP-I{N}-{ID} — {short title}
- **SEVERITY:** FAIL | CONCERN | OBSERVATION
- **LOCATION:** {file} §{section}
- **GAP:** {what is missing or wrong}
- **RESOLUTION:** {what was changed}
- **STATUS:** APPLIED | BACKLOG
```

Each iteration's gap-analysis report is written into the active task folder
(`process/features/{feature}/active/{slug}_{date}/{slug}-iteration-{NNN}_REPORT_{date}.md`,
`{NNN}` zero-padded to 3 digits), following Rule 1 — task-folder artefact colocation.

---

## TSV log (machine-readable trend data)

One TSV file per loop run at `process/features/{feature}/active/{task-slug}_{dd-mm-yy}/results.tsv`, co-located with the iteration report in the same task folder.

Each row = one iteration:

```
iteration | timestamp | gaps_found | fail_count | concern_count | applied | saturation_status | loop_status | notes
0         | ...       | 20         | 3          | 12            | 0       | ACTIVE            | CONTINUE    | baseline
1         | ...       | 15         | 1          | 11            | 14      | ACTIVE            | CONTINUE    | iteration 1 apply complete
2         | ...       | 8          | 0          | 7             | 8       | ACTIVE            | CONTINUE    | iteration 2 apply complete
3         | ...       | 3          | 0          | 3             | 3       | PLATEAU           | CONTINUE    | gap velocity slowing
4         | ...       | 0          | 0          | 0             | 0       | SATURATED         | HALTED_SUCCESS | all agents ALL_CLEAR
```

The TSV complements the .md reports: use TSV for trend analysis across iterations, use .md for per-gap audit trail.

---

## Relationship to the autoresearch reference repo

The external autoresearch tool at `Agent-Software-Development-Harness/autoresearch` is:
- Single-agent, sequential
- Metric-driven only (needs a shell command that returns a number)
- Commits each change to git, reverts on failure
- 13 subcommands for different loop shapes (fix, debug, probe, reason, etc.)

vc-autoresearch differs:
- Multi-agent parallel (N research agents + M fix agents running simultaneously)
- Verdict-driven OR metric-driven
- Report-based (no per-iteration git commits during the loop)
- Fewer subcommands — only the ones not already covered by existing vc-system skills

Already covered by existing skills (don't port): debug → vc-debugger, security → vc-security, scenario → vc-scenario, predict → vc-predict.

Useful to port: core loop mechanics, probe (8-persona saturation), reason (adversarial debate with blind judges), evals (TSV trend analysis).

**Hook conflict note:** autoresearch hooks are installed at `.claude/hooks/autoresearch/`. Do NOT register scout-block or privacy-block from that set — the vc-system already has superior versions registered in settings.json. Only iteration-context.cjs and stop-notify.cjs are safe to keep.

---

## Implementation backlog

- [ ] Write SKILL.md at `.claude/skills/vc-autoresearch/SKILL.md`
- [ ] Remove `vc-autoresearch` from the Removed Skills table in vc-system-behavior-reference.md (prerequisite before any implementation)
- [ ] Add `ALL_CLEAR` and `REGRESSION_DETECTED` to signal vocabulary in vc-system-behavior-reference.md
- [ ] Add entry to CLAUDE.md skill registry (under contract skills)
- [ ] Annotate PVL and EVL sections in vc-system-behavior-reference.md with "vc-autoresearch(domain=plan)" and "vc-autoresearch(domain=execution)" for clarity
- [ ] Adapt `iteration-context.cjs` hook from autoresearch repo: scan `process/features/*/active/*/results.tsv` (not project-root `autoresearch/` paths); additive injection only, do not duplicate vc-system fields
- [ ] Adapt `session-init.cjs`: path change `plans/` → `process/general-plans/active/` and `process/features/*/active/`
- [ ] Skip `scout-block.cjs` and `privacy-block.cjs` — vc-system settings.json has superior versions; registering these would create CRITICAL conflicts
- [ ] Define probe and reason subcommand specs (for adversarial debate and persona saturation loops)
- [ ] Decide: should UPDATE PROCESS optionally trigger autoresearch(domain=docs) as a closeout step?
- [ ] Update path references in this spec once task-folder-framework plan executes (Phase 8c of that plan)

---

## Resolved decisions

**D1 — Git commits during loop:** No per-iteration git commits. The autoresearch repo commits each iteration to enable `git revert` rollbacks; vc-autoresearch uses iteration reports + TSV instead. Regression detection (5 in termination conditions above) is the rollback signal — a REGRESSION halt lets the user inspect and revert manually. Single conventional commit via vc-git-manager at loop end (or not at all if the session continues to further phases). Rationale: keeps git history clean, avoids "WIP iteration N" noise in log.

**D2 — PVL user gate:** PVL prompts once at kickoff: "Auto-run (no pauses) or confirm before each fix batch?" Sticky for the full loop. Under `/goal`, always auto. PVL is NOT restricted to `/goal` contexts — the kickoff prompt handles the V5 gate for manual sessions. Under auto mode, V5 auto-decides (no pause); under confirm mode, user reviews before each supplement batch is applied.

**D3 — TSV file location:** TSV goes inside the task folder alongside the iteration report — `process/features/{feature}/active/{task-slug}_{dd-mm-yy}/results.tsv`. Follows the task-folder framework (canonical rules in `process/development-protocols/plan-lifecycle.md` §Task-Folder Framework). The `iteration-context.cjs` hook must scan `process/features/*/active/*/results.tsv` rather than project-root `autoresearch/` paths.
