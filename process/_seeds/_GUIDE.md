# Process Directory

This is the operational workspace for the agent harness. It holds context, plans, features, protocols, and seeds.

## Directory Structure

process/
  _seeds/                  -- seed templates (read-only reference, never modified during setup)
  context/                 -- durable project knowledge (all-context.md is the root router)
  development-protocols/   -- managed methodology docs (RIPER-5, orchestration, standards)
  features/                -- feature-scoped storage (plans, reports, references per feature)
  general-plans/           -- cross-cutting plans, reports, and references
    active/                -- in-progress plans (each plan lives inside a {slug}_{date}/ task folder)
    completed/             -- archived completed plans
    backlog/               -- deferred/future plans

## Key Conventions

- `all-*.md` files are routing entrypoints -- read them first, then drill down
- `_GUIDE.md` files explain what goes in each folder
- `.seed` files in `_seeds/` are structural templates showing the expected shape of each file
- Feature folders are created when a feature has 5+ artifacts or 3+ planned phases
- Plans use date-stamped names: `{feature}_PLAN_{dd-mm-yy}.md`
- Context group seed folders in `_seeds/` use `-seed` suffix (e.g., `tests-seed/`, `planning-seed/`)

## Seeds vs Real Files

- `_seeds/` contains structural templates -- read-only during setup, never modified
- Real files in `context/`, `features/`, `general-plans/` contain actual project content
- SCAFFOLD phase copies seed structure to create real working folders
- STUDY phase reads seeds for section guidance, writes real content to working folders
- Seeds are maintained for reference and future harness updates (vc-update)
