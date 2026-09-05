---
name: protocol:plan-lifecycle
description: "How plans are named, where they live, when to use feature folders, EXECUTE handoff, and how mixed legacy plan shapes are treated."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 4
  required: false
  read_when: "creating, naming, locating, archiving, or resuming a plan, or choosing feature-scoped storage"
---

# Plan Lifecycle

## Canonical Plan Surface

Default active-plan locations:

- `process/general-plans/active/`
- `process/features/{feature}/active/`

Default naming for new direct plan files:

- `{slug}_PLAN_{dd-mm-yy}.md` (the `{slug}` is the task slug — e.g. `model-selector_PLAN_09-06-26.md`, not a literal `[feature]` placeholder)

The active inventory is intentionally mixed right now. Treat these as compatibility shapes during scans and resume flows:

- direct `*_PLAN_*.md` files
- legacy `PLAN.md`
- legacy `plan.md`
- legacy `phase-*.md` siblings or plan folders

New work ALWAYS uses the direct `*_PLAN_*.md` / task-folder convention. The legacy shapes above are READ-ONLY compatibility shapes for audits and resume flows — they are never a new-write target. When resuming work that already lives in a legacy structure, keep editing in place (do not force a migration mid-flight), but any genuinely new plan is written in the canonical shape.

## Feature Folder Routing

Use `process/features/{feature}/` when:

- the feature folder already exists
- the topic clearly belongs to an existing feature
- the work is a new multi-phase project
- the user frames it as a substantial product area

Otherwise use `process/general-plans/`.

If the work is a large multi-phase program, also apply `phase-programs.md`:

- create one umbrella orchestration plan
- create one explicit plan file per phase
- expect each phase to have its own report and validation checkpoint

Feature folder structure (new repos):

- `active/` — task subfolders `{slug}_{dd-mm-yy}/` containing plan + colocated artifacts
- `completed/` — archived task subfolders (same shape; no prefix added)
- `backlog/` — flat NOTE files

Legacy repos may also have:
- `reports/` — legacy read-only sibling dir (deprecated for new writes)
- `references/` — legacy read-only sibling dir (deprecated for new writes)

## Phase-Program Folder Layout

A multi-phase program does NOT use per-phase subfolders. The whole program lives FLAT
inside ONE task folder `{program-slug}_{date}/` that moves as a unit on completion.
`phase-programs.md` is canonical for the full loop; this is the durable folder shape:

```text
process/features/{feature}/
  active/
    {program-slug}_{date}/
      {program-slug}-umbrella_PLAN_{date}.md          <- umbrella; frontmatter `phase: umbrella` AND filename MUST contain the `umbrella` token (validator-enforced)
      phase-01-{slug}_PLAN_{date}.md
      phase-01-{slug}_REPORT_{date}.md         <- co-located FLAT after execution
      phase-02-{slug}_PLAN_{date}.md
      phase-02-{slug}_REPORT_{date}.md
      phase-blast-radius-registry.md           <- one registry for the whole program
      {slug}_REF_{date}.md                     <- references, also FLAT
  completed/
  backlog/
```

Every phase plan, report, the single blast-radius registry, and references live FLAT
inside that one `{program-slug}_{date}/` folder. There are NO per-phase subfolders.
The umbrella plan is validated by `validate-umbrella-artifact.mjs` (single writer:
the phase-program owner) and must carry frontmatter `phase: umbrella`.

## Feature Folder Lifecycle

**At plan creation time — decision logic:**

| Signal | Action |
|--------|--------|
| `process/features/{topic}/` already exists | Use it — pass `Feature: {topic}` to subagent |
| Topic clearly belongs to an existing feature | Use that feature's folder |
| New multi-phase project (3+ planned phases) | Create feature folder upfront |
| User says "this is a big feature" or names a product area | Create feature folder upfront |
| Single plan, no backlog, unclear scope | Use `process/general-plans/active/` (general) |
| Cross-cutting work touching multiple features | Use general folders |

**Promotion protocol (general → feature folder):**

When general artifacts for a single topic reach 5+, or when a user requests it:
1. Create `process/features/{new-feature}/` with subdirs: `active/`, `completed/`, `backlog/` (do NOT create `reports/` or `references/` — these are deprecated for new repos)
2. Move related artifacts from `process/general-plans/` into the new feature's task folders; legacy `reports/` and `references/` content moves into appropriate task folders
3. Update the **Current features** list in `process/context/all-context.md`
4. Inform subagents of the new feature scope going forward

**Feature list maintenance:** The current features list in `process/context/all-context.md` must be updated whenever a new feature folder is created or an empty one is removed. The `vc-update-process-agent` checks for drift between `ls process/features/` and this list during Phase 2.

### Closed Feature State

Some mature feature folders may intentionally stop carrying live `active/` work for a period.

- This is allowed when the feature is effectively complete or intentionally frozen.
- The folder should still keep `completed/` and `backlog/` as needed. Legacy `reports/` and `references/` may remain as read-only sibling dirs.
- Document the closed/no-active state in a local status file such as `README.md` when doing so avoids routing confusion.
- Orchestrators must not assume every existing feature folder currently has active plan files.

## Resume and Execute Handoff

- Always scan both active-plan surfaces before creating a new plan.
- If overlapping active plans exist, update or resume them instead of duplicating work.
- Before EXECUTE, confirm exactly one selected plan file path.
- Pass that exact plan file path into the execute handoff.
- Never rely on ambient active-plan state alone when multiple active plan artifacts exist.
- When passing a plan to execute-agent, also pass the validate-contract section or note whether VALIDATE was skipped and why.

### Legacy Multi-File Handoff Rule

When the active work uses a legacy structure such as `PLAN.md` plus `phase-*.md` files:

- choose one primary plan file path as the execute anchor
- pass supporting phase files explicitly as additional context
- do not tell the worker to infer the plan from a folder name alone
- prefer normalizing to a direct `*_PLAN_*.md` file only when the user has approved cleanup or the ongoing work naturally justifies it
- treat missing execute-anchor or supporting-file notes as compatibility warnings first, not blockers, unless a later stricter migration is explicitly approved

## Plan-File Frontmatter

Every plan `.md` file — direct `*_PLAN_*.md` files and any plan `.md` inside a `{slug}_{date}/`
task folder — MUST start with a YAML frontmatter block. This mirrors the context-doc frontmatter
convention (`node_type: memory`) already in use across context and protocol docs in this repo:

```yaml
---
name: plan:{slug}
description: "{one-line plan summary}"
date: {dd-mm-yy}
metadata:
  node_type: memory
  type: plan
---
```

**Required fields:**

| Field | Value |
|-------|-------|
| `name` | `plan:{slug}` — where `{slug}` is the kebab-case task slug matching the filename (e.g. `plan:model-selector`) |
| `description` | One-line plain-English summary of what the plan covers |
| `date` | Today in `dd-mm-yy` format (e.g. `16-06-26` for 16 June 2026) |
| `metadata.node_type` | Always `memory` — matches the convention used by context docs, protocol docs, and skill references |
| `metadata.type` | One of: `plan` · `phase-plan` · `umbrella` · `reference` · `implementation` |

**`status` is optional** — omit it unless the plan explicitly tracks lifecycle state in frontmatter.

**Allowed `metadata.type` values:** `plan` · `phase-plan` · `umbrella` · `reference` · `implementation`

**Date format note:** `dd-mm-yy` is the canonical plan date format (e.g. `16-06-26`). Use the
two-digit year form matching context and protocol docs in this repo.

**Umbrella plans** use `type: umbrella`. Per-phase plans use `type: phase-plan`.

Legacy plans that predate this convention are treated as warnings by the validator, not hard
failures. Add frontmatter to legacy plans opportunistically when they are next touched.

## Stronger Direct-Plan Contract

For new or newly touched direct `*_PLAN_*.md` files, required sections are defined in
`.claude/skills/vc-generate-plan/SKILL.md`. Use Markdown-structured sections, not a second
machine-only schema.

## Reports and References

New artifacts follow the task-folder convention — co-located inside the task folder:
- Feature-specific reports: `process/features/{feature}/active/{slug}_{date}/{slug}_REPORT_{date}.md`
- Feature-specific references: `process/features/{feature}/active/{slug}_{date}/{slug}_REF_{date}.md`
- Cross-cutting reports and references: `process/general-plans/active/{slug}_{date}/{slug}_REPORT_{date}.md`

Legacy paths (deprecated for new writes; existing content is read-only):
- `process/general-plans/reports/` — legacy cross-cutting reports; `reports/visuals/` stays for binary assets
- `process/general-plans/references/` — legacy cross-cutting research
- `process/features/{feature}/reports/` — legacy feature reports
- `process/features/{feature}/references/` — legacy feature references

Migration expectation:
- `vc-setup` and `vc-update` should migrate safe legacy `reports/` / `references/` artifacts into the relevant task folder when exactly one destination task folder can be inferred in the same scope.
- After safe migration, remove the emptied legacy sibling dir so the target steady-state is `active/`, `completed/`, and `backlog/` only.
- Leave ambiguous, shared, or unowned legacy artifacts in place and surface them for manual review rather than forcing a risky move.

## Backlog

- Cross-cutting deferred work belongs in `process/general-plans/backlog/`.
- Feature-specific deferred work belongs in `process/features/{feature}/backlog/`.
- Use backlog for actionable follow-up work, not finished reports or durable reference material.
- Use references for research outputs that inform future decisions.
- Move an item from `active/` to backlog when it is intentionally deferred but still actionable.

## Archiving

- Completed general plans move to `process/general-plans/completed/`.
- Completed feature plans move to `process/features/{feature}/completed/`.
- Preserve historical artifacts unless the user explicitly asks for normalization or cleanup.

### Archive-Readiness Semantics

Do not treat every successful code change as immediately archive-ready.

Use these states:

- **Ready to archive**
  - the selected plan path still matches the implemented work
  - required verification evidence exists
  - no material deviations remain unresolved
  - the user has confirmed or approved cleanup
  - validate-contract is present in the plan file, or VALIDATE was explicitly skipped with a documented reason
- **Keep in active / testing**
  - implementation is substantially complete
  - but testing, manual verification, or explicit user confirmation is still pending
- **Needs reconciliation before archival**
  - material deviations from the selected plan were required
  - context/process updates are needed before the plan can be archived
  - the work should route through UPDATE PROCESS or back to PLAN first

For non-trivial work, prefer routing archive decisions through UPDATE PROCESS so context updates, lessons learned, and selected-plan archival happen together.

## Closeout Packet And Move-On Rule

For non-trivial work, a selected plan should not end with only "done" or "still testing."

Full closeout packet schema, drift scoring, archive-readiness states, and move-on
next-state examples: invoke `vc-generate-closeout`.

## Task-Folder Framework

Every task's artifacts — plan, spec, reports, and references — live together under one named subfolder inside `active/` or `completed/`. When a task completes, the whole task folder moves as a unit.

### Task Folder Naming

- Task folder: `{slug}_{dd-mm-yy}/` inside `active/` or `completed/`
- Files inside: `{slug}_{TYPE}_{dd-mm-yy}.md` where TYPE is one of: `PLAN`, `SPEC`, `REPORT`, `REF`
- Slug uses lowercase kebab-case, consistent across all files in the folder
- Date is the task creation date (not the migration date)
- Task folder name is STABLE — it does NOT gain a `completed_` prefix when archived; `active/foo_08-06-26/` moves to `completed/foo_08-06-26/` unchanged
- Task folder contents are flat — no subfolders inside task folders

### Artifact Types

| TYPE | Purpose |
|------|---------|
| `PLAN` | Implementation plan — one per task, required |
| `SPEC` | Living specification — process rules, behavior reference, architecture spec |
| `REPORT` | Execution report, audit, research output for this task |
| `REF` | Reference material, external research, source snapshots |

### Lifecycle Rule

1. Create task folder in `active/{slug}_{date}/` with `_PLAN_` file inside.
2. Add `_REPORT_`, `_REF_`, or `_SPEC_` files to the same folder as work progresses.
3. On completion, `git mv active/{slug}_{date}/ completed/{slug}_{date}/` — the whole folder moves.

### Backlog Rule

`backlog/` stays flat. NOTE files and deferred items do not get task subfolders. Only full `_PLAN_` files (with `type: plan` frontmatter) may be wrapped in a task folder when promoted to backlog from active.

### Reports and References

Feature-specific reports and references are colocated inside their task folder. The sibling `reports/` and `references/` directories under feature roots and `process/general-plans/` are deprecated going forward — do not add new files there.

### Rule 1 — Task-Folder Artefact Colocation (mandatory)

Every artefact produced while working a task — plan, spec, reports, references, audit
outputs, autoresearch iteration reports + `results.tsv`, closeout packets, and
research/scratch notes — MUST be written inside that task's folder:

- Feature-scoped: `process/features/{feature}/active/{slug}_{dd-mm-yy}/`
- General: `process/general-plans/active/{slug}_{dd-mm-yy}/`

Never write task artefacts to the deprecated sibling `reports/`/`references/` directories,
nor to ad-hoc locations. When the task completes, the whole folder moves as a unit
(`active/` → `completed/`, later → `backlog/` if deferred). Because the folder moves as
one unit, every artefact stays found relative to its siblings.

This rule is greppable as the phrase **"task-folder artefact colocation"** across agent
definitions and skills, which all defer here for the canonical statement.

### Rule 2 — No Durable→Movable References (mandatory)

Durable files MUST NOT link to a SPECIFIC movable task artefact. Durable files are:
`process/context/**`, `process/development-protocols/**`, `.claude/agents/**`,
`.claude/skills/**`.

A "specific movable task artefact" is a concrete `*_PLAN_*.md` / `*_SPEC_*.md` /
`*_REPORT_*.md` / `*_REF_*.md` / `*_NOTE_*.md` / `*_CHECKPOINT_*.md` filename, or a
specific `{slug}_{date}/` task folder under `active/` | `completed/` | `backlog/`. These
references rot constantly: task folders move between `active/`/`completed/`/`backlog/`, and
feature folders get renamed.

What to do instead:

- **Durable knowledge** (conventions, architecture, patterns, decisions) → INLINE it
  directly into the durable doc. Do not leave it parked in a task report that a context
  doc points at.
- **Task-scoped detail** (one task's execution evidence) → stays inside the task folder.
  Durable docs simply do not point at it.
- **Pattern paths are fine**: `active/{slug}_{date}/` and bare directory roots like
  `process/features/{feature}/active/` are conventions, not references — keep those.

When durable knowledge currently lives only in a task report, migrate it: copy the minimal
durable fact into the appropriate `process/context/` doc, then drop the pointer.

### Backward Compatibility

During the migration window, agents must tolerate both shapes:
- flat `*_PLAN_*.md` files at `active/` root (legacy, being migrated)
- task folder `{slug}_{date}/{slug}_PLAN_{date}.md` (new canonical shape)

Both are valid until migration is complete. New plans must use the task-folder shape.
