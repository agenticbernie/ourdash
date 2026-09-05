---
name: protocol:context-maintenance
description: "How process/context/ is organized, when to create or split groups, and how durable knowledge differs from feature plans."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 6
  required: false
  read_when: "maintaining context docs, creating/splitting context groups, or keeping all-context.md accurate"
---

# Context Maintenance

## Purpose

`process/context/` is the durable shared project-knowledge layer for agents. It is not the same as feature planning or tool-specific memory.

Use it for stable operational knowledge such as:

- architecture and routing
- testing procedures
- debugging procedures
- deployment and infrastructure flows
- UI or workflow conventions

## Read Order

Before reading `all-context.md`, run `find process/context/ -type f | sort` to get the full listing of all context files. This prevents silently skipping a context file that is not yet indexed by the router.

1. Read `process/context/all-context.md` first.
2. Load only the relevant root file or context-group entrypoint.
3. Follow that entrypoint into deeper docs only when needed.
4. If the task vocabulary does not obviously map to a routing row, run `node .claude/skills/vc-context-discovery/scripts/discover-context.mjs --match "<task>"` to rank docs by frontmatter `keywords` instead of guessing, then load any `related:` siblings it surfaces.

## Frontmatter Contract

Every context doc (including each `all-{group}.md`) carries routing frontmatter — see the canonical schema in `vc-context-discovery`:

- `keywords` (recommended, non-empty): task-vocabulary terms; the match surface for `--match`. Lint warns when empty; backfill at UPDATE-PROCESS.
- `related` (optional): `context:{slug}` siblings usually needed together. Every slug must resolve to a real doc.

The "Current Root Entry Points" and "Current Context Groups" tables in `all-context.md` are GENERATED from this frontmatter, between `<!-- GENERATED:routing -->` markers. Never hand-edit them — edit the owning doc's frontmatter and re-emit.

## Context Groups

Context groups are durable knowledge domains, not feature folders.

Every group should have an `all-{group}.md` entrypoint that includes:

- scope
- read-when rules
- quick procedures
- source paths
- update triggers
- routing to deeper docs

## When to Create or Split a Group

Create or promote a context group when any of these are true:

- the topic has 3 or more durable docs
- a single doc grows beyond roughly 800 lines and contains separable subtopics
- multiple agents repeatedly need only one slice of a large context file

## Update Rules

- Update the owning context docs whenever code or workflow behavior changes what those docs describe.
- When a durable entrypoint is added, renamed, grouped, or removed, edit the doc's frontmatter (`description`/`keywords`/`related`), then regenerate the router tables: `node .claude/skills/vc-context-discovery/scripts/discover-context.mjs --emit-routing`. Do not hand-edit the generated tables in `all-context.md`.
- Move or split one group at a time so discovery changes stay reviewable.
- After context-organization changes, run the `vc-audit-context` skill or its validators (this includes a `--check-routing` drift check that fails if the generated block is stale).

## Relationship to Tool Memory

- Claude may also maintain its own project-memory layer under `~/.claude/projects/.../memory/`.
- Codex does not have a repo-local project-memory mirror in this repo.
- Durable shared knowledge that both systems should rely on belongs in `process/context/`.
