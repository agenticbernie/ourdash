# ourdash - All Context

Last updated: 2026-09-05

This file is the root context entrypoint for the repo.

`ourdash` is a modern Python SDK for Dash (dash.org crypto — not Plotly Dash) covering Dash Core (RPC, wallet/tx, P2P/network) + Dash Platform (DAPI, Drive, identities, DPNS, tokens). Audience: app developers + analysts. Solo-maintained, strict quality (pytest + ruff + black + mypy strict). v0.1 shipped: typed Core reads, offline P2PKH payment pipeline, Platform reads with proof verdicts (`src/ourdash/`, 17 modules).

Use it for two things:

1. quick routing to the right context pack or root file
2. broad architecture and repository understanding

Start here before loading deeper context files. The context router is `process/context/all-context.md` — always load it first.

---

## How This File Works (the `all-*.md` Convention)

Every `process/context/` directory has one `all-*.md` entrypoint that acts as an attachable quick router for that domain. This root file (`all-context.md`) is the top-level router. Context groups each have their own `all-{group}.md` entrypoint.

**The pattern:**

```
process/context/
  all-context.md                      <-- THIS FILE: root router
  planning/
    all-planning.md                   <-- group router for planning
  tests/
    all-tests.md                      <-- group router for tests
```

**How agents use it:**

1. Agent reads `all-context.md` first (this file)
2. Finds the relevant context group from the routing tables below
3. Reads that group's `all-{group}.md` entrypoint
4. Only then loads the specific deep doc needed

This layered routing keeps context windows small. Never load the whole `process/context/` tree.

**What each `all-{group}.md` must contain:**

- Scope (what the group covers and does NOT cover)
- Read-when rules (when an agent should load this group)
- Quick procedures or decision rules
- Source paths (list of deeper docs in the group)
- Update triggers (when to refresh this group's content)
- Routing to deeper docs within the group

---

## Quick Start

For most substantial tasks:

1. read this file first
2. choose the smallest relevant root file or context group from the tables below
3. only then load deeper files

---

## Current Root Entry Points

<!-- The two tables below (Root Entry Points + Context Groups) are GENERATED from each
     context doc's frontmatter by `discover-context.mjs --emit-routing`. Do NOT hand-edit
     between the GENERATED markers — your edits will be overwritten on the next rebuild.
     To change a row, edit the owning doc's frontmatter (description / keywords) and re-emit.
     `--check-routing` fails lint if this block drifts from the frontmatter on disk. -->

<!-- GENERATED:routing -->
| File | Read when |
|---|---|
| `process/context/all-context.md` | any substantial planning, research, review, or implementation task |
| `process/context/planning/all-planning.md` | Planning entrypoint — SIMPLE vs COMPLEX calibration and plan-shape references |
| `process/context/tests/all-tests.md` | Testing entrypoint — pytest runner, commands, debugging, quality gates |

## Current Context Groups

| Group | Entry point | Scope |
|---|---|---|
| `planning/` | `process/context/planning/all-planning.md` | Planning entrypoint — SIMPLE vs COMPLEX calibration and plan-shape references |
| `tests/` | `process/context/tests/all-tests.md` | Testing entrypoint — pytest runner, commands, debugging, quality gates |
<!-- /GENERATED:routing -->

## Task Routing Table

| Task type | Load first | Then load |
|---|---|---|
| general repo research | `all-context.md` | domain file named by task |
| Dash Core RPC / wallet / tx | `all-context.md` | `src/ourdash/core/` + docs.dash.org Core RPC refs below |
| Dash Platform DAPI / Drive / identities | `all-context.md` | `src/ourdash/platform/` + docs.dash.org Platform refs below |
| implementation planning | `all-context.md`, `process/context/planning/all-planning.md` | the relevant active plan in `process/general-plans/active/` |
| test planning or verification | `all-context.md`, `process/context/tests/all-tests.md` | `pytest -q`, `mypy src`, `ruff check` |
| debugging | `all-context.md`, `process/context/tests/all-tests.md` when tests/runtime are involved | smallest domain doc + `tests/test_import.py` |
| context maintenance | `all-context.md` | run `audit-context` after edits |

## Context Group Lifecycle

Context groups are durable knowledge domains, not feature folders.

Create a group when:

- a topic has 3+ durable docs
- a single doc exceeds roughly 800 lines with separable subtopics
- multiple agents repeatedly need only one slice of a large context file
- the topic maps to a stable operational domain (tests, infra, database, auth, UI, workflows, etc.)

Do not create a group when:

- the content is a temporary report
- the content is a plan or execution artifact
- the topic is feature-specific and belongs in feature folders under process/features/

Move or split one group at a time. Use `all-{group}.md` entrypoints. Run the `audit-context` skill after every context organization change.

Current groups: `planning/` (plan-shape calibration), `tests/` (pytest/quality gates). No `database/`, `auth/`, `container/`, `infra/`, `uxui/`, `workflows/` groups — SDK has no DB, no auth provider, no Docker, no UI; create only when 2+ source files justify it.

## Naming Convention

There are no `README.md` files inside `process/context/`.

Canonical entrypoints use `all-*.md`:

- root: `process/context/all-context.md`
- group: `process/context/{group}/all-{group}.md`

Each `all-{group}.md` file should act as the attachable quick router for that domain:

- tell the agent what the group covers
- give quick procedures and decision rules
- route to smaller deeper files

Critical naming guard: PyPI `dash` is Plotly Dash (dashboard framework), not Dash crypto. This repo's package is `ourdash`. Never `pip install dash` expecting crypto. Always disambiguate as "Dash (dash.org)" vs "Plotly Dash".

## Context Update Protocol

When durable project knowledge changes:

1. update the smallest relevant context file
2. update this file if routing, ownership, naming, or groups changed
3. update the owning `all-{group}.md` entrypoint when a group exists
4. run `audit-context`

---

## Repository Structure

```
ourdash/
  pyproject.toml          -- hatchling build, src layout, pytest/ruff/black/mypy config (+ `hybrid`/`agent_probe` markers)
  README.md               -- install, layout, Dash refs, quality gates
  .github/workflows/ci.yml -- pytest (non-hybrid/probe) + ruff + black --check + mypy, Python 3.10–3.12
  src/ourdash/            -- 17 modules (v0.1 final)
    __init__.py           -- __version__ = 0.1.0, top-level re-exports
    errors.py             -- typed taxonomy (RpcError, DAPIError, PaymentError, ProofError, …)
    redact.py             -- secrets redaction choke point
    core/
      rpc.py              -- DashRPC + DashRPCConfig (transport: call/batch/from_env, dataclasses-only)
      addresses.py        -- P2PKH/version-byte validation + network/kind facade
      transactions.py     -- offline P2PKH build/review/sign/submit-refusal + finality status
      wallet.py           -- BIP39 restore → BIP32/44 (coin type 5), watch-only default
      chain.py            -- typed Core read facade (info/block/tx/balance/multi-wallet)
      network.py          -- chaintips, masternode-list diff, ChainLock tip status
    platform/
      dapi.py             -- DAPIClient + DAPIConfig (address defaults None; from_network())
      seeds.py            -- per-network seed discovery (no hardcoded default URL)
      models.py           -- pydantic facade models + ProofVerdict
      proofs.py           -- verifier contract + FakeVerifier + reference-bridge boundary
      drive.py            -- documents/identity/DPNS/token query facade
    utils/
      __init__.py         -- base58-checksum/hash helpers
  tests/                  -- 185 collected / 7 deselected (hybrid + agent_probe); conftest regtest fixture; fixtures/platform/ recorded proof envelopes
    conftest.py + test_*.py (13 files incl. test_seam.py, test_secrets.py)
    fixtures/platform/    -- recorded proof envelopes (DPNS/identity/token)
  docs/                   -- install, connect, first-payment-testnet, first-platform-read, troubleshooting (+ platform/)
  process/
    context/              -- this context system (all-context.md router)
    general-plans/        -- active/completed/backlog (task-folder convention; v0.1 program archived under completed/ourdash-sdk_04-09-26/)
    features/             -- feature-scoped storage (_GUIDE.md only until 5+ artifacts)
    development-protocols/-- RIPER-5 methodology docs
```

## Technology Stack

- **Language:** Python `>=3.10` (local `3.14.6`; CI targets `3.10–3.12`)
- **Build:** `hatchling`, `src/` layout, package `ourdash==0.1.0`
- **Core deps:** `requests>=2.31` (RPC), `pydantic>=2.0` (schemas), `base58>=2.1`, `bech32>=1.2`
- **Platform extras:** `grpcio>=1.60`, `protobuf>=4.25` (`pip install -e ".[platform]"`)
- **Dev/quality:** `pytest>=8.0`, `pytest-cov>=5.0`, `ruff>=0.4` (line-length 100, py310), `black>=24.0`, `mypy>=1.10` strict
- **Dash Core:** `dashd` JSON-RPC over HTTP POST — mainnet `9998`, testnet `19998`, regtest `19898`; HTTP basic auth (`rpcuser`/`rpcpassword` or cookie); `dash-cli` as CLI reference; multi-wallet since Core 18 (`-rpcwallet`); batch JSON-RPC 2.0; sub-command RPCs (`protx`, `masternode`, `quorum`, `gobject`); ChainLocks (quorum-signed blocks, active since block 1088640, Jun 2019 — no reorg below a locked block) + InstantSend (original Transaction-Locking form + current deterministic LLMQ form; DIP0024 defines quorum rotation only and invented neither) (SPEC Constraints: Protocol facts; Finality model)
- **Dash Platform:** DAPI (gRPC for L2 + streaming, JSON-RPC for L1 info), Drive (GroveDB-backed L2 storage on masternodes), DPP (data contracts as JSON Schema, documents like MongoDB, state transitions signed by identity keys), identities/DPNS/tokens; JS refs `@dashevo/dapi-client`, `dash-sdk` in `dashpay/platform` monorepo. v0.1 proof model: `platform/proofs.py` verifier contract + `FakeVerifier` + pinned reference-bridge boundary (greenfield pure-Python port NOT attempted); every Platform read returns data + `ProofVerdict`, explicit keyword-only `trust_node=False` fallback labels `UNCHECKED` + `UserWarning`
- **Package manager:** `pip` + `pyproject.toml` (no poetry/pdm lock yet); venv `.venv`; editable install required for `src/` layout (`pip install -e ".[all]"`, else `ModuleNotFoundError: ourdash`)
- **Test suite (v0.1 final):** 185 collected / 7 deselected via `-m "not hybrid and not agent_probe"`; markers `hybrid` (regtest `dashd` / recorded fixtures) + `agent_probe` (live testnet, never CI) registered in `pyproject.toml`; regtest fixture in `tests/conftest.py` (skips without binary); recorded proof envelopes in `tests/fixtures/platform/`; suite + `ruff` + `black --check` + `mypy src` green; fresh-checkout proof green; live testnet reads recorded
- **Monorepo:** no — single package
- **Existing Python Dash libs (gap):** `dashcommunity/Dashpylib` (thin `dash-cli` wrapper returning JSON), `mMeinhardt/DashPy` (CLI wallet over DAPI); no mature typed SDK — `ourdash` fills this

## Key Patterns and Conventions

**Error handling:** typed taxonomy in `errors.py` (`RpcError` with code/message, `DAPIError` with proofs, `PaymentError`, `ProofError`, …) + `requests` retries/timeouts; transport failures map to distinct typed errors. No silent `None` returns.

**Import style:** `from ourdash.core.rpc import DashRPC, DashRPCConfig`; `from ourdash.platform.dapi import DAPIClient`. Absolute imports only. `src/` layout requires editable install.

**Config pattern:** frozen dataclasses (`DashRPCConfig`, `DAPIConfig`) with sane loopback defaults (`127.0.0.1:9998`; DAPI has NO default address — per-network seed discovery via `platform/seeds.py`, never-ship rule per SPEC Constraints: Platform access). Env overrides planned: `OURDASH_RPC_URL`, `OURDASH_DAPI_ADDRESS` (names only, no values in repo).

**Naming:** `snake_case` modules/functions, `PascalCase` classes, `UPPER_SNAKE` env constants. Kebab-case feature folders, `{slug}_{dd-mm-yy}/` task folders.

**File colocation:** Core vs Platform split is hard boundary — `src/ourdash/core/` never imports from `platform/`; shared code goes in `src/ourdash/utils/`.

**Docs discipline:** every module docstring lists its canonical upstream ref (docs.dash.org URL family + JS-SDK equivalent). Disambiguate Dash crypto vs Plotly Dash in every public doc.

**Solo workflow:** trunk-based, small PRs, `pytest -q && mypy src && ruff check` before every commit. Plans live in task folders under `process/general-plans/active/` — no legacy layout.

## Environment and Configuration

**Config files:** `pyproject.toml` (build + pytest/ruff/black/mypy), `.venv/` (git-ignored), `.gitignore` (has `.vibecode-backup*/` + Python ignores to add: `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `dist/`, `build/`, `*.egg-info/`)

**Env var groups (names only, never values):**

- Core RPC: `OURDASH_RPC_URL`, `OURDASH_RPC_USER`, `OURDASH_RPC_PASSWORD`, `OURDASH_RPC_WALLET`
- Platform: `OURDASH_DAPI_ADDRESS`, `OURDASH_DAPI_TIMEOUT_S`
- Network selection: `OURDASH_NETWORK` (`mainnet|testnet|regtest|devnet`)
- Dash native (`dash.conf` parity): `rpcuser`, `rpcpassword`, `rpcport`, `server`, `rpcwhitelist`

**Service locations:**

- Core RPC default `http://127.0.0.1:9998` (testnet `19998`, regtest `19898`)
- DAPI endpoints resolve per network via `platform/seeds.py` (documented seeds; empty-list-with-reason where none are documented) — no default URL ships; the `api.dash.org` placeholder never resolved (SPEC Constraints: Platform access)
- Upstream code: `dashpay/dash` (Core), `dashpay/platform` (Platform), `dashpay/docs-*`

## References and Key Files

- `pyproject.toml` — stack + quality gates source of truth
- `src/ourdash/core/rpc.py` — Core RPC stub + port/auth notes
- `src/ourdash/platform/dapi.py` — Platform DAPI stub
- `README.md` — install + layout + Dash refs
- `process/context/tests/all-tests.md` — pytest/mypy/ruff commands
- `process/context/planning/all-planning.md` — SIMPLE vs COMPLEX calibration
- Upstream: `https://www.dash.org`, `https://docs.dash.org` (Core RPC + Platform DAPI/Drive/DPP), `https://github.com/dashpay/platform`, `https://github.com/dashpay/dash`

## Open Questions

- RESOLVED (v0.1): Dash Core v23.1.8 (SPEC Constraints: Core compatibility pin). Method allowlist pinned from the v23.1.8 sources; `dash-cli help` live dump still pending (no binary in dev env).
- DAPI endpoint versioning: which gRPC proto version + JSON-RPC surface to target first (`getDocuments`, Core `getBlock` parity)?
- Address version bytes + X11 hashing libs in pure Python vs `hashlib` + native bindings?
- RESOLVED (v0.1): wallet scope is recovery-phrase restore + BIP44 (coin type 5) signing, always with custody warnings and watch-only default (SPEC Constraints: Wallet scope). Signing fence shipped P2PKH-only: P2SH/multisig/script paths raise `PaymentError` (explicit deferral, enforced by `tests/test_transactions.py`).
- RESOLVED (v0.1): Platform proof model shipped as verifier contract + `FakeVerifier` + pinned reference-bridge boundary in `platform/proofs.py` (greenfield pure-Python port NOT attempted); every Platform read returns data + `ProofVerdict` over recorded fixtures in `tests/fixtures/platform/`.
- Testnet vs regtest for CI live-integration (regtest preferred, needs `dashd` fixture)?
- License confirmed MIT? Author/maintainer + repo URL for `pyproject.toml`?
- RESOLVED (v0.1): `.github/workflows/ci.yml` added in Phase 1 (SPEC Validation: automation workflow in v0.1).

## Scan Metadata

- Generated: 2026-09-05
- HEAD: 61699da (feat phases 1–6 on master; prior 0bbf7ca harness scaffold)
- Mode: v0.1 SDK program complete (plans archived under `process/general-plans/completed/ourdash-sdk_04-09-26/`)
- Package manager: pip + hatchling (`pyproject.toml`, no lockfile)
- Kit: vibecode-pro-max-kit v3.2.5, Flow A New Project
- Detected context groups: planning, tests (no database/auth/container/infra/uxui/workflows — insufficient signals)
- Detected feature areas: dash-core, dash-platform (deferred as feature folders until 5+ artifacts; v0.1 program archived in `process/general-plans/completed/`)
