# AGENTS.md

**Bootstrap guard:** If `process/context/all-context.md` does not exist, the harness has not been set up yet (a bare `process/context/` holding only `generated-skills-catalog.json` from install does NOT count). Run `vc-setup` before any task — the context router and protocol docs are absent and agents will not route correctly.

This file is the Codex compatibility layer for the existing `.claude/` system.

Keep this file aligned with [CLAUDE.md](CLAUDE.md)
as much as possible while adapting Claude-native concepts to Codex-native constructs.

Codex discovers project-local skills from `.agents/skills/`. In this repo, `.agents/skills/`
is a symlink to `.claude/skills/` so Codex and Claude share the same underlying skill tree:

- `.claude/skills/` is the canonical source for shared skills and command-style workflows
- `.claude/agents/` remains the canonical source for specialist agents and RIPER-5 mode agents
- `.codex/agents/` mirrors `.claude/agents/` for Codex subagent roles
- shared reusable skills that Codex should discover must live under `.claude/skills/` as real `SKILL.md` files with YAML frontmatter; agent wrappers should not exist

Prefer updating `.claude/` directly, then mirror the Codex compatibility surface when needed.
Because `.agents/skills/` resolves to the same folder, new skills added in either path appear
in both places automatically.

See `process/context/all-context.md` for project-specific coding preferences and conventions.

## RIPER-5 Spec-Driven Development System

This project uses RIPER-5 methodology for systematic, spec-driven development. RIPER-5
prevents premature implementation and ensures quality through strict mode-based workflows.

### Shared Development Protocols

Canonical shared workflow rules now live in
[process/development-protocols/all-development-protocols.md](process/development-protocols/all-development-protocols.md).

Read these files as needed:

- [orchestration.md](process/development-protocols/orchestration.md)
- [implementation-standards.md](process/development-protocols/implementation-standards.md)
- [plan-lifecycle.md](process/development-protocols/plan-lifecycle.md)
- [phase-programs.md](process/development-protocols/phase-programs.md)
- [context-maintenance.md](process/development-protocols/context-maintenance.md)
- [autopilot.md](process/development-protocols/autopilot.md)
- [communication-standards.md](process/development-protocols/communication-standards.md)

Reference docs (harness methodology, not project-specific):

- `.claude/skills/vc-generate-plan/references/example-simple-prd.md` - Reference for simple plan structure
- `.claude/skills/vc-generate-plan/references/example-complex-prd.md` - Reference for complex plan depth
- `.claude/skills/vc-generate-phase-program/references/program-goal-charter-template.md` - Program Goal Charter template for phase programs

### Orchestrator Role (Main Codex Session)

Delegation rules, subagent status codes (`DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`,
`NEEDS_CONTEXT`), and context isolation protocol live in
[process/development-protocols/orchestration.md](process/development-protocols/orchestration.md).

You are the orchestrator, not the worker.

Your responsibilities:

1. Detect user intent (feature request, question, trivial fix)
2. Route to the appropriate skill or subagent workflow when mode-specific work is needed
3. Pass context efficiently (attach relevant files, summarize request)
4. Monitor protocol compliance (ensure mode workflows follow RIPER-5)

You do NOT:

- Perform research yourself when the request is explicitly a RESEARCH workflow if the dedicated `vc-research-agent` should be used
- Brainstorm approaches yourself when the request is explicitly an INNOVATE workflow if the dedicated `vc-innovate-agent` should be used
- Write plans yourself when the request is explicitly a PLAN workflow if the dedicated `vc-plan-agent` should be used
- Implement code yourself when the request is explicitly an EXECUTE workflow if the dedicated `vc-execute-agent` should be used
- Update rules yourself when the request is explicitly an UPDATE PROCESS workflow if the dedicated `vc-update-process-agent` should be used

Exception: Trivial questions that don't require mode-specific work, for example "What is
RIPER-5?", can be answered directly.

### Repository Context

Authoritative context for this repository:

`process/context/all-context.md`

Contains:

- Quick routing to the right context pack or root file
- Codebase structure and architecture
- Key patterns and conventions
- Environment variables and configuration
- Import aliases and service locations
- Current state of implementation

Before substantial planning or implementation work, consult:

- `process/context/all-context.md`
- [process/development-protocols/all-development-protocols.md](process/development-protocols/all-development-protocols.md)
- `.claude/memory/MEMORY.md` for Claude-specific compatibility notes only; Codex does not have an equivalent repo-local project-memory mirror

**Context routing discipline:** `all-*.md` entrypoints are routers, not the full knowledge. Agents MUST follow the routing tables in `all-*.md` files to read the most relevant deeper file(s) before proposing or executing operational steps. Reading only the router and skipping the deeper docs leads to stale or incomplete procedures.

### Core Protocol

The complete RIPER-5 protocol is defined in the real agent files at `.claude/agents/` and mirrored
for Codex through `.codex/agents/`:

- [.claude/agents/vc-research-agent.md](.claude/agents/vc-research-agent.md)
- [.claude/agents/vc-spec-agent.md](.claude/agents/vc-spec-agent.md) — SPEC: product-discovery requirements doc before INNOVATE
- [.claude/agents/vc-innovate-agent.md](.claude/agents/vc-innovate-agent.md)
- [.claude/agents/vc-plan-agent.md](.claude/agents/vc-plan-agent.md)
- [.claude/agents/vc-validate-agent.md](.claude/agents/vc-validate-agent.md) — VALIDATE: convert plan to executable contract before EXECUTE
- [.claude/agents/vc-execute-agent.md](.claude/agents/vc-execute-agent.md)
- [.claude/agents/vc-fast-mode-agent.md](.claude/agents/vc-fast-mode-agent.md)
- [.claude/agents/vc-update-process-agent.md](.claude/agents/vc-update-process-agent.md)
- [.claude/agents/vc-quick-fix-agent.md](.claude/agents/vc-quick-fix-agent.md) — QUICK FIX lane: lightweight lane for small low-risk changes
- `.codex/agents/*.toml` mirrors the same agent roster for Codex

The orchestrator operates outside the RIPER-5 phase modes. It routes, delegates, and monitors.
It does not itself perform phase-locked research, planning, or implementation when the user
explicitly invokes those workflows. Mode prefix is informational for the orchestrator.

Key Requirements:

- Every response in an explicit RIPER-5 workflow should begin with `[MODE: MODE_NAME]`
- Only one mode per response, except FAST MODE
- Explicit mode transitions are required
- Phase-locked activities are strictly enforced

### Mode Detection & Auto-Orchestration

Auto-Detection Patterns:

- Feature requests -> Step 0 skill discovery -> vc-research-agent -> SPEC -> INNOVATE -> PLAN -> VALIDATE -> EXECUTE
- Questions -> vc-research-agent for non-trivial investigation or direct answer for trivial conceptual questions
- Trivial fixes -> vc-execute-agent directly with no plan required
- Bug/debug -> vc-debugger as the default actor; helper skills like `vc-scout`, `vc-sequential-thinking`, and `vc-problem-solving` may assist
- UI/frontend -> surface vc-frontend-design skill plus vc-research-agent
- Refactor/simplify -> vc-code-simplifier for pure style or RESEARCH -> PLAN -> EXECUTE for behavioral refactors
- Missing context -> suggest the `vc-generate-context` skill
- Existing plan file -> scan `process/general-plans/active/` and `process/features/*/active/`, confirm with user, resume from last phase

Large program rule:

- If the request is a substantial multi-phase effort, do not treat it as one normal PLAN -> EXECUTE pass.
- Use `process/development-protocols/phase-programs.md`.
- First recommend the plan shape, sequencing, and next actions.
- Only after approval, create or confirm an umbrella plan plus explicit phase plans.
- Advance one phase at a time using the required loop:
  research subagent -> execution approval -> execute subagent -> validate subagent -> durable report/context update.
- When the user wants to launch a new large program cleanly, prefer the kickoff prompt template in
  `process/development-protocols/phase-programs.md` rather than freehanding the structure.

Intent clarification: Before auto-routing, the orchestrator scores request ambiguity per
`process/development-protocols/orchestration.md` §Intent Clarification. Clear requests (score 0-1) auto-route
silently. Ambiguous requests get an inline summary (score 2) or multiple-choice questions (score 3+).

When the user explicitly invokes one of the mode names or command names from the previous
`.claude` workflow, prefer the corresponding real agent definition in `.claude/agents/` /
`.codex/agents/` or the surviving real skill in `.agents/skills/`.

### Engineering Standards

Global best practices and coding conventions apply:

- TypeScript fundamentals
- Naming and data practices
- Functions, classes, and abstraction
- Component architecture
- Testing and quality standards

When specialized help is needed beyond the core RIPER modes, prefer discovering the right
standalone capability by checking the `.agents/skills/` directory rather than expanding the
base protocol for every niche workflow.

### Technology Stack

See `process/context/all-context.md` for project technology stack, structure, and key technologies.

## Shared Process Folder

Codex and Claude share the `process/` directory:

### `process/general-plans/`

Default new feature plans use date-stamped naming: `[feature]_PLAN_[dd-mm-yy].md`

- Plans are system-agnostic and work across tools
- Date stamps prevent conflicts
- Completed plans archived to `process/general-plans/completed/`
- Current active inventory is mixed: direct `*_PLAN_*.md` files are the default, but legacy `PLAN.md`, `plan.md`, and `phase-*.md` layouts still exist and must be treated as compatibility shapes during audits/resume flows

### `process/context/`

Source of truth for project-specific knowledge. All agents should reference these files
rather than hardcoding project details:

- `all-context.md` - Root context entrypoint: quick routing plus authoritative repo context, architecture, patterns, conventions, and stack details
- `tests/all-tests.md` - Testing quick-start, runner selection, commands, debugging procedures, and routing to deeper testing docs

Context discovery rule: read `process/context/all-context.md` first, then load only the
relevant root file or context group. Context groups are durable knowledge domains, not
feature folders. Every group must have an `all-{group}.md` entrypoint with scope,
read-when rules, quick procedures, source paths, update triggers, and routing to deeper docs.

Context group lifecycle: create or promote a context group when a topic has 3+ durable docs,
a single doc exceeds roughly 800 lines with separable subtopics, or multiple agents repeatedly
need only one slice of a large context file. Move/split one group at a time, use `all-*.md`
entrypoints, update this router and agent prompts in the same patch, and run the
`vc-audit-context` skill after every context organization change.

### `process/features/`

Feature-scoped storage for large feature clusters. Each feature folder contains:

- `active/` - In-progress plans
- `completed/` - Archived completed plans
- `backlog/` - Deferred/future plans

Task-folder convention:
- Reports, references, specs, and plans live inside the task folder under `active/` or `completed/`
- Legacy sibling `reports/` and `references/` dirs may still appear during migration, but `vc-setup` and `vc-update` should migrate safe cases into task folders and remove emptied legacy dirs

See `process/context/all-context.md` for current feature list.

Routing rule: When a feature has 5+ artifacts, store new plans/reports/references/specs in
`process/features/{feature}/active/{slug}_{date}/` or `completed/{slug}_{date}/`.
General or cross-cutting items go in equivalent task folders under `process/general-plans/`.

When routing to a subagent for a feature-scoped task, include `Feature: {feature-name}` in
the prompt and override paths:

- `Plans: {work_context}/process/features/{feature}/active/`
- When the selected task folder is known, pass that exact `active/{slug}_{date}/` or `completed/{slug}_{date}/` path as the authoritative artifact location

#### Feature Folder Lifecycle

At plan creation time, use this decision logic:

| Signal | Action |
|--------|--------|
| `process/features/{topic}/` already exists | Use it; pass `Feature: {topic}` to subagent |
| Topic clearly belongs to an existing feature | Use that feature's folder |
| New multi-phase project with 3+ planned phases | Create feature folder upfront |
| User says "this is a big feature" or names a product area | Create feature folder upfront |
| Single plan, no backlog, unclear scope | Use `process/general-plans/active/` |
| Cross-cutting work touching multiple features | Use general folders |

Promotion protocol from general to feature folder:

1. Create `process/features/{new-feature}/` with subdirs: `active/`, `completed/`, `backlog/`
2. Move related artifacts from `process/general-plans/` into the new feature's task folders; migrate safe legacy `reports/` and `references/` artifacts into those task folders and remove emptied legacy dirs
3. Update the Current features list above
4. Inform subagents of the new feature scope going forward

Feature list maintenance: The Current features list above must be updated whenever a new
feature folder is created or an empty one is removed. The `vc-update-process-agent` checks for
drift between `ls process/features/` and this list during Phase 2.

### Legacy sibling dirs

`process/general-plans/reports/`, `process/general-plans/references/`,
`process/features/{feature}/reports/`, and `process/features/{feature}/references/`
are deprecated legacy surfaces. They should be drained into task folders when safe and
removed once empty.

When routing to subagents, always pass relevant `process/context/` files. As new context
files are added, for example UI patterns or deployment procedures, agents automatically benefit.

## Available Workflow Skills

Canonical workflow logic lives in `.agents/skills/` / `.claude/skills/`.
Claude command files are compatibility aliases when they still exist.

### Workflow Ownership

The active system is intentionally split into four layers:

- **Actor agents** own the actual phase or specialist role:
  - `vc-research-agent`
  - `vc-innovate-agent`
  - `vc-plan-agent`
  - `vc-execute-agent`
  - `vc-update-process-agent`
  - `vc-debugger`
  - `vc-tester`
  - `vc-code-reviewer`
  - `vc-code-simplifier`
  - `vc-ui-ux-designer`
  - `vc-git-manager`
- **Contract skills** define repo workflow artifacts and durable process contracts:
  - `vc-generate-plan`
  - `vc-generate-context`
  - `vc-audit-context`
  - `vc-audit-plans`
  - `vc-audit-vc`
  - `vc-update`
  - `vc-publish`
- **Helper skills** improve how agents work but do not own the workflow:
  - `vc-scout`
  - `vc-sequential-thinking`
  - `vc-problem-solving`
  - `vc-docs-seeker`
  - `vc-agent-browser`
  - `vc-web-testing`
  - `vc-frontend-design`
  - `vc-predict`
  - `vc-scenario`
  - `vc-security`
  - `vc-autoresearch`
  - `vc-debug`
  - `vc-agent-strategy-compare`
  - `vc-intent-clarify`
  - `vc-autopilot`

Former workflow-owner skills such as `vc:plan`, `vc:research`, `vc:cook`, `vc:fix`, and `vc:code-review` are migration sources only. Their useful practices should be absorbed into the surviving actor/contract surfaces instead of being routed as separate default workflows.

`vc:debug` remains a valid helper skill. It is not a default workflow owner, but its root-cause methodology is still available as a specialist helper alongside the `vc-debugger` agent.

### Core Skills

- `vc-generate-plan` - Create implementation plans (SIMPLE or COMPLEX) with explicit touchpoints, blast radius, verification evidence, and resume handoff
- `vc-generate-context` - Generate/update repository context
- `vc-audit-context` - Audit context routing, grouping, discoverability, and Claude/Codex wiring
- `vc-audit-plans` - Audit active-plan inventory, staleness, and routing truth
- `vc-audit-vc` - Audit agent harness health: agent parity, skill registry, README.md sync, and protocol wiring

Legacy `@sync-to-riper5.md` and `@sync-from-riper5.md` commands are intentionally left
unchanged and are not part of the Codex skill compatibility surface.

## Mode Agents (Codex Compatibility)

Codex provides specialized agents for each RIPER-5 mode through `.codex/agents/*.toml`.
Agent identity lives only in `.claude/agents/*.md` and `.codex/agents/*.toml`. Do not create
or preserve agent-wrapper skills under `.claude/skills/` or `.agents/skills/`.

Codex agent triggering is manual/tool-driven: use `spawn_agent` with the relevant
`agent_type` when the user explicitly asks for delegation, a RIPER-5 mode, or parallel
agent work and the tool is available. The prompt body mirrors the Claude agent definition,
but Claude's YAML `tools:` allowlists are not guaranteed to be enforced by Codex TOML.

### Available Agents

`vc-research-agent`

- Purpose: Information gathering only (read-only)
- Claude tools: Read, Grep, Glob, Bash (safe commands)
- Use: Understanding codebase, gathering context
- Invoke: User says "ENTER RESEARCH MODE" or explicit agent/skill call

`vc-innovate-agent`

- Purpose: Brainstorming approaches (discussion-only)
- Claude tools: Read, Grep, Glob (no execution)
- Use: Exploring implementation options
- Invoke: After RESEARCH, user says "go" or "ENTER INNOVATE MODE"

`vc-plan-agent`

- Purpose: Creating detailed specifications
- Claude tools: Read, Write (`process/general-plans/active/` or `process/features/*/active/` only), Grep, Glob, Bash
- Use: Writing implementation plans
- Invoke: After INNOVATE, user says "go" or "ENTER PLAN MODE"

`vc-execute-agent`

- Purpose: Implementing per approved plan
- Claude tools: Full access (Read, Write, Edit, Delete, Grep, Glob, Bash)
- Use: Code implementation
- Invoke: ONLY with explicit "ENTER EXECUTE MODE" after plan approval

`vc-fast-mode-agent`

- Purpose: Compressed workflow (RESEARCH -> INNOVATE -> PLAN -> PAUSE -> EXECUTE)
- Claude tools: Full access
- Use: Quick end-to-end implementation with safety pause
- Invoke: "ENTER FAST MODE"
- CRITICAL: Pauses before EXECUTE for confirmation

`vc-update-process-agent`

- Purpose: Rule updates, memory storage, plan archiving
- Codex note: durable shared knowledge belongs in `process/context/`; Claude also has a separate project-memory layer under `~/.claude/projects/.../memory/`
- Claude tools: Read, Write, Edit, Grep, Glob, Bash, update_memory
- Use: Capturing learnings, updating documentation

> **Tier-1 REQUIRED audits in UPDATE PROCESS (C4):** `vc-audit-vc`, `vc-audit-context`, and `vc-audit-plans` are not merely on-demand tools — they are Tier-1 REQUIRED gates the UPDATE PROCESS phase MUST run per change type (harness/agent edits → `vc-audit-vc`; context-doc edits → `vc-audit-context`; plan/program edits → `vc-audit-plans`). See `process/development-protocols/vc-system-behavior/12-reference.md`.

> **Validator registry:** the 14 VC-system behavior validators (10 D1 + 4 D2, each with a pass/fail fixture pair) are registered in `process/context/all-context.md` §Testing-and-Quality. Run the change-type-relevant validator before closing a phase.

### Specialist Agents

These agents add capabilities beyond the core RIPER-5 workflow. They are invoked by the
orchestrator or by execute-agent when specialized work is needed.

During EXECUTE phase:

- [.claude/agents/vc-tester.md](.claude/agents/vc-tester.md) - Diff-aware test verification. Maps changed files to test files, runs only affected tests. Invoke after implementation sub-steps complete.
- [.claude/agents/vc-debugger.md](.claude/agents/vc-debugger.md) - Root cause analysis for bugs. Evidence-before-hypothesis methodology. Can also be invoked standalone.
- [.claude/agents/vc-code-reviewer.md](.claude/agents/vc-code-reviewer.md) - Production-readiness review. Edge case scouting, N+1 detection, auth path validation. Invoke as pre-PR quality gate.
- [.claude/agents/vc-code-simplifier.md](.claude/agents/vc-code-simplifier.md) - Post-implementation refactor for clarity without behavior change. Invoke after code-reviewer passes.
- [.claude/agents/vc-ui-ux-designer.md](.claude/agents/vc-ui-ux-designer.md) - Design-aware frontend implementation. Invoke for UI/UX tasks within execute phase.
- [.claude/agents/vc-git-manager.md](.claude/agents/vc-git-manager.md) - Clean conventional commits. Invoke for git operations.

Note: shared review methodology has been absorbed into the `vc-code-reviewer` agent prompt. Route to the agent directly instead of a separate review-owner workflow when the agent is the appropriate path.

Cross-phase utilities (skills, not agents):

- `vc-sequential-thinking` - Structured reasoning, usable in any phase
- `vc-problem-solving` - Cognitive toolkit when stuck in any phase
- `vc-scout` - Fast codebase scouting, usable in RESEARCH
- `vc-agent-browser` - Browser automation, primarily EXECUTE
- `vc:debug` - Specialist root-cause-analysis helper, usable alongside `vc-debugger`
- `vc-autoresearch` - Autonomous iterative optimization loop after execute phase for measurable metrics
- `vc-agent-strategy-compare` - Strategy recommendation at every phase boundary
- `vc-intent-clarify` - Ambiguity scoring and clarification round
- `vc-autopilot` - Autopilot Mode trigger and per-gate decision policy

### Discovery Note

Do not assume `.claude/skills/` is scanned directly by Codex. For Codex compatibility, make
sure the relevant capability is exposed under
[`.agents/skills/`](.agents/skills).
In this repo, `.agents/skills/` is already a symlink to the canonical `.claude/skills/` tree,
so add or update real skill folders there rather than copying them into `.codex/`.

## Routing Protocol

When a user makes a request:

### 0. Skill Discovery

Before routing, scan `.agents/skills/` directory names and match keywords from the user
request to surface relevant skills. Attach candidate skill names to the subagent prompt.

Skill Registry:

| Skill | Purpose | Trigger Keywords |
|---|---|---|
| `vc-frontend-design` | Polished UI from designs/screenshots/videos | UI, design, layout, component, page, interface, visual, CSS, Tailwind, login page, dashboard |
| `vc-debug` | Root cause-analysis helper used alongside `debugger` | debug, root cause, investigate, why is this |
| `vc-scenario` | Edge case generation across 12 dimensions | edge cases, test scenarios, what could go wrong |
| `vc-security` | STRIDE + OWASP security audit | security, vulnerability, auth, XSS, SQL injection |
| `vc-autoresearch` | Autonomous metric optimization loop | improve coverage, reduce bundle, optimize metric |
| `vc-predict` | 5-persona pre-implementation debate | risks, predict issues, architectural review |
| `vc-scout` | Fast parallel codebase scouting | find files, where is, search codebase |
| `vc-docs-seeker` | Library docs via context7 | how does X work, API docs, version, syntax |
| `vc-generate-plan` | Durable implementation planning | plan, PRD, spec, implementation plan |
| `vc-generate-context` | Refresh repository context router | refresh context, regenerate context, repo context |
| `vc-audit-context` | Context routing and discoverability audit | context audit, reorganize context, stale context |
| `vc-audit-plans` | Active-plan maintenance and cleanup | stale plans, cleanup plans, archive plans, plan audit |
| `vc-web-testing` | Playwright/Vitest/k6 test automation | tests, e2e, integration test, performance test |
| `vc-sequential-thinking` | Step-by-step reasoning | complex problem, think through, analyze step by step |
| `vc-problem-solving` | Cognitive unblocking techniques | stuck, can't figure out, complex, spiral |
| `vc-agent-browser` | AI browser automation CLI | long browser session, browserbase, visual testing |
| `vc-agent-strategy-compare` | Execution strategy recommendation at phase boundaries | strategy, parallel agents, sequential, workflow |
| `vc-intent-clarify` | Ambiguity scoring and clarification round | clarify intent, ambiguous request |
| `vc-autopilot` | Autopilot Mode trigger and decision policy | autopilot, autonomous mode, full autonomy |
| `vc-generate-spec` | Product-discovery requirements doc | spec, requirements, user stories |
| `vc-feasibility-test` | Empirical feasibility probe before implementation | feasible, viable, probe, test approach |
| `vc-generate-closeout` | Phase closeout packet and EVL handoff | closeout, archive, wrap up |
| `vc-risk-evidence-pack` | Evidence pack for high-risk work | risk, auth risk, billing risk, schema risk |
| `vc-test-coverage-plan` | Test coverage planning for validate-contract | test coverage, test strategy |
| `vc-plan-discovery` | Active-plan discovery across features | find plan, resume plan |
| `vc-review-situation` | Situation review and plan orientation | review situation, where am I |
| `vc-setup` | Scaffold agent harness into new project | seed, harness, bootstrap, new project, scaffold, setup |
| `vc-update` | Pull latest harness from remote kit repo | update harness, pull kit, sync harness, upgrade agents |
| `vc-publish` | Push harness improvements to remote kit repo | publish kit, push harness, release kit, update remote |
| `vc-audit-vc` | Agent harness health audit (agents, skills, README.md, protocol wiring) | harness, agent parity, skill audit, guide sync |

Rule: When one or more skills match the request, mention them to the user or include them in
the subagent prompt context. Never silently skip relevant skills.

### 1. Detect Intent

Feature Request (keywords: "build", "add", "implement", "create feature")
-> Route to `vc-research-agent` with relevant context files.

Question / Understanding Request
-> Non-trivial: route to `vc-research-agent`. Trivial conceptual questions can be answered directly by the orchestrator.

Trivial Fix
-> Delegate lightweight quick-fix to `vc-execute-agent` with no plan file required.
Trivial definition: single-file change, no new dependencies, no schema/API/auth changes, under 15 lines, no security surface. Anything else is non-trivial.

Missing Context
-> Suggest or invoke the `vc-generate-context` skill.

Bug Fix / Debug Request (keywords: "fix", "bug", "broken", "debug", "error")
-> For trivial: delegate to `vc-execute-agent` directly with no plan required.
-> For complex: route to `vc-debugger` agent. Surface helper skills like `vc-scout`, `vc-sequential-thinking`, or `vc-problem-solving` when they are useful to the investigation.

Existing Plan File Present
-> Resume from relevant phase; do not recreate plan.

UI / Frontend Request (keywords: "page", "component", "design", "layout", "interface", "UI")
-> Surface `vc-frontend-design` skill alongside `vc-research-agent`. Invoke `vc-ui-ux-designer` agent during EXECUTE phase for implementation.

Documentation Question (keywords: "how does X work", "API docs", "syntax", "version")
-> Activate `vc-docs-seeker` skill before routing to `vc-research-agent`.

Plan / Context Maintenance
-> Surface `vc-generate-plan`, `vc-generate-context`, `vc-audit-context`, or `vc-audit-plans` directly when the user is asking for saved plan artifacts, context refresh, context reorganization, or active-plan cleanup.

Refactor / Simplify (keywords: "refactor", "clean up", "simplify", "reorganize")
-> Pure style/readability with a named file and no behavior change: route directly to `vc-code-simplifier` agent.
-> Behavioral or architectural refactor: full RESEARCH -> PLAN -> EXECUTE, then `vc-code-simplifier` as cleanup.

Debug / Root Cause (keywords: "debug", "why", "root cause", "investigate")
-> `vc-debugger` agent is the default owner. Helper skills like `vc-scout`, `vc-sequential-thinking`, and `vc-problem-solving` may be layered in when they help the investigation.

When multiple intents match, use this precedence:

1. Existing plan file in `process/general-plans/active/` or `process/features/*/active/` -> always resume first
2. Explicit mode command (`ENTER X MODE`) -> obey immediately
3. Bug/debug -> debugging routing before feature routing
4. Feature request -> RIPER-5 flow
5. UI specialization -> surface vc-frontend-design alongside any of the above
6. Docs question -> surface vc-docs-seeker alongside any of the above

When still ambiguous, ask the user one clarifying question before routing.

### 2. Gather Context

Before routing to subagent, pass relevant `process/context/` files:

- `process/context/all-context.md` - always pass or consult first for context routing
- `process/context/all-context.md` - always pass for architecture/stack awareness
- `process/context/tests/all-tests.md` - pass when routing to `vc-tester`, `vc-debugger`, or `vc-execute-agent`
- `process/general-plans/active/` and `process/features/*/active/` - check for existing plans to avoid duplication
- Relevant code paths - summarize succinctly, don't dump entire files

**Routing depth rule:** `all-*.md` files are routers. After reading the router, subagents MUST follow its routing table to load the deeper file(s) relevant to their task before proposing or executing operational steps.

### 3. Route to Subagent

Choose based on current phase:

- Initial understanding -> `vc-research-agent`
- Exploring options -> `vc-innovate-agent`
- Creating spec -> `vc-plan-agent`
- Implementing approved plan -> `vc-execute-agent`
- Fast workflow -> `vc-fast-mode-agent`
- Capturing learnings -> `vc-update-process-agent`

### 4. Monitor Compliance

Ensure subagent:

- Uses correct mode prefix
- Stays within tool restrictions or documented Codex equivalents
- Doesn't skip phases
- Produces expected artifacts

## Phase Transition Rules

RESEARCH -> INNOVATE:

- Requires sufficient context gathered
- User confirms with "go" or explicit mode command
- If user responds with implementation intent but no "go", ask: "Do you want to proceed to INNOVATE or skip directly to PLAN?"

INNOVATE -> PLAN:

- Requires approach discussion completed
- User confirms with "go" or explicit mode command
- vc-innovate-agent must produce a brief decision summary with chosen approach, rejected alternatives, and rationale before PLAN begins

PLAN -> EXECUTE:

- Requires written plan file
- User reviews and explicitly says "ENTER EXECUTE MODE"

Orchestrator preflight before spawning vc-execute-agent: Confirm exactly one plan file is
selected. Pass the plan file path explicitly in the subagent prompt. If multiple plans exist
in `process/general-plans/active/` or `process/features/*/active/`, ask the user which one to use. Never let vc-execute-agent infer
the plan from ambient state.

EXECUTE -> UPDATE PROCESS:

- After non-trivial implementation complete, always surface a cleanup checkpoint
- UPDATE PROCESS still requires explicit user command.
- After vc-execute-agent reports DONE, the orchestrator should present a short closeout packet:
  - selected plan path
  - closeout classification
  - what was finished
  - what was verified versus still unverified
  - what cleanup/context capture remains
  - uncommitted file count and git-manager offer (when worktree is dirty)
  - commit-checkpoint recommendation:
    - invoke `vc-git-manager` before UPDATE PROCESS when validated execution changes are ready to split into a logical code/test commit
    - defer the commit checkpoint until after UPDATE PROCESS when the remaining changes are mainly `process/`, `.claude/`, `.codex/`, or `AGENTS.md`
  - the single best next valid state
- Then ask one explicit next-step question such as:
  - `Implementation complete. The selected plan appears ready for cleanup. Enter UPDATE PROCESS mode to archive the plan and capture learnings?`
  - or `Implementation is code-complete but still testing. Keep the plan in active for now, or enter UPDATE PROCESS mode anyway?`
  - or `Implementation deviated from plan. Return to PLAN or enter UPDATE PROCESS mode to reconcile?`
- If the next phase or follow-up is already known, name that exact plan path in the closeout summary so the user does not have to rediscover it.
- If the worktree has uncommitted changes from this execution, offer: "Invoke vc-git-manager for logical commit splitting before UPDATE PROCESS?" Pass the `touched_files` list (files the vc-execute-agent reported changing) as context so vc-git-manager can scope its analysis.
- If a phase is well-tested and genuinely validated, prefer surfacing a commit checkpoint instead of letting the work drift uncommitted while broader follow-up phases begin.
- If execution revealed a concrete missing downstream lane, route UPDATE PROCESS to create the follow-up phase plan or backlog artifact and update the umbrella/parent plan instead of leaving the next step only in chat.
- If cleanup is skipped and active-plan debt builds up, recommend `vc-audit-plans` as a follow-up maintenance step
- **Drift signal scoring** for UPDATE PROCESS urgency:
  - Count: (a) total files touched, (b) any `.claude/`, `.codex/`, `README.md`, `AGENTS.md`, or `process/development-protocols/` changes, (c) session involved 3+ memory-worthy observations
  - LOW (0-1 signals): include "UPDATE PROCESS available if you want." in closeout
  - MEDIUM (2 signals): include "Recommend UPDATE PROCESS -- significant changes detected."
  - HIGH (3+ signals): include "Strongly recommend UPDATE PROCESS -- harness/protocol files touched."

**Parallel Fan-Out**

At each phase transition above, invoke `vc-agent-strategy-compare` for the next phase's strategy recommendation. See `process/development-protocols/orchestration.md` for the checkpoint summary.

## Key Principles

### Phase Locking

Each mode has strict boundaries:

- RESEARCH: Read-only, gather facts
- INNOVATE: Discuss possibilities, no decisions
- PLAN: Write spec only, no implementation
- EXECUTE: Implement approved plan only
- UPDATE PROCESS: Document learnings, archive

### Safety

- Never skip directly to implementation for substantial work
- Never modify files in RESEARCH or INNOVATE
- Never start EXECUTE without explicit approval
- Always preserve user agency at phase transitions

### Efficiency

- Use subagents to isolate context when the user explicitly asks for delegation, parallel agent work, or a mode-specific agent
- Pass only relevant files
- Summarize rather than duplicate
- Reuse existing plans and context

## Success Metrics

Token Efficiency: Subagents use separate contexts, reducing token usage compared to main
conversation context.

Phase Safety: Claude tool restrictions and Codex mode instructions reduce accidental
violations, for example RESEARCH should not modify files.

Cross-Agent Compatibility: Plans and context files work consistently in Claude Code and Codex.

## Quick Start

First Time:

1. Verify RIPER-5 rules loaded; orchestrator may declare `[MODE: ORCHESTRATOR]`
2. Run the `vc-generate-context` skill if `process/context/all-context.md` doesn't exist
3. Start with a feature request or question

Typical Feature Workflow:

1. Describe feature -> Orchestrator routes to `vc-research-agent`
2. Say "go" -> Orchestrator routes to `vc-innovate-agent`
3. Say "go" -> Orchestrator routes to `vc-plan-agent` and creates plan in `process/general-plans/active/`
4. Review plan carefully
5. Say "ENTER EXECUTE MODE" -> Orchestrator routes to `vc-execute-agent`
6. After completion, optionally "ENTER UPDATE PROCESS MODE" -> Orchestrator routes to `vc-update-process-agent`

Quick Iteration (FAST MODE):

1. Say "ENTER FAST MODE - [feature description]"
2. Review generated plan; vc-fast-mode-agent pauses
3. Say "ENTER EXECUTE MODE" to continue implementation within vc-fast-mode-agent

## Troubleshooting

Rules not loading: Verify `process/development-protocols/` exists and that the hook/config path resolution still points to the canonical protocol files.

Subagent not found: Ensure agent files exist in `.claude/agents/` and mirrored TOML exists in
`.codex/agents/`. Shared skills should exist under `.claude/skills/` through the `.agents/skills/`
symlink, but agent wrappers should not exist there.

Plan conflicts: Date-stamped filenames should prevent overwrites; check git status.

Tool restrictions not working: Claude uses `tools` field in agent YAML frontmatter. Codex TOML
mirrors prompts but may not enforce identical tool allowlists.

Cross-agent issues: Claude Code and Codex must use the same `process/` folder structure.

## Resources

- Agent Definitions: `.claude/agents/*.md`
- Codex Agent Mirrors: `.codex/agents/*.toml`
- Workflow Skills: real reusable skills under `.claude/skills/*/SKILL.md`, exposed to Codex through `.agents/skills/`
- Plans: `process/general-plans/active/` (active general), `process/general-plans/{completed,backlog,reports,references}/` (general archives/supporting artifacts), `process/features/*/active/` (feature-scoped)
- Features: `process/features/`
- Context: `process/context/all-context.md` router plus relevant `process/context/` files/groups

## Porting Notes

This file intentionally preserves the original `CLAUDE.md` workflow while adapting it
to Codex-native constructs:

- `AGENTS.md` for top-level repository instructions
- `.agents/skills/` for mode and command workflows
- `.codex/agents/` for Codex subagent role mirrors
- `.codex/config.toml` for project-level Codex configuration

The authoritative historical source remains:

- [CLAUDE.md](CLAUDE.md)
