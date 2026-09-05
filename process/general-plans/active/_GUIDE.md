# Active Plans

This folder holds implementation plans that are currently in progress.

## Naming Convention

Plans use the **task-folder convention**: create a subfolder `{slug}_{dd-mm-yy}/` and place the plan file inside it.

```
active/
  user-auth_15-03-26/
    user-auth_PLAN_15-03-26.md
    user-auth_SPEC_15-03-26.md      (optional — if SPEC was written)
  dashboard-redesign_22-04-26/
    dashboard-redesign_PLAN_22-04-26.md
```

Each task folder is the single home for all artifacts belonging to that plan: the plan file, specs, iteration reports, feasibility verdicts, and results.tsv. Do NOT create `reports/` or `references/` sibling dirs — those are deprecated; all colocated artifacts go inside the task folder.

Old flat naming (`user-auth_PLAN_15-03-26.md` directly in `active/`) is a legacy shape — treat as read-only. New plans always use the task-folder convention.

## What Goes Here

- Plans that are actively being implemented
- Plans that have been approved but not yet started
- Plans waiting for EXECUTE mode approval

## What Does Not Go Here

- Completed plans (move to `completed/`)
- Deferred or future work (move to `backlog/`)
- Reports or references (colocate inside the task folder, not as sibling dirs)

## Lifecycle

1. Task folder + plan file created during PLAN mode
2. Plan is executed during EXECUTE mode
3. After completion and verification, move the whole task folder to `completed/`
4. If deferred, move the whole task folder to `backlog/`
