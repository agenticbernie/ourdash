# ourdash SDK v0.1 — UMBRELLA Build Plan (Trust-Ladder Hybrid)

Date: 04-09-26. Status: ⏳ PLANNED. Complexity: COMPLEX (phase program).

**Date**: 04-09-26
**Status**: ⏳ PLANNED
**Complexity**: COMPLEX (phase program)

Task folder: `process/general-plans/active/ourdash-sdk_04-09-26/`
Locked SPEC: `ourdash-sdk_SPEC_04-09-26.md` (18 criteria, Open Questions: None).
Decision Summary: Approach C (trust-ladder hybrid) chosen over A (weak typed/offline story) and B (oversized cost + audit surface).

TL;DR: Build `ourdash` v0.1 in 6 strictly sequential phases — transport+safety+CI, addresses, offline wallet slice, Core reads, Platform reads facade + proof port, docs + secret-scan + clean-gate — with disjoint file ownership per phase.

## Quick Links

- [Goal](#goal) · [Chosen Approach](#chosen-approach) · [Phase Map](#phase-map) · [Proof Boundaries](#per-phase-proof-boundaries) · [Ownership](#shared-file-ownership-map) · [Test Matrix](#full-test-matrix) · [Rollback](#rollback-notes) · [Success](#success-criteria) · [Resume](#resume-and-execution-handoff)

## Overview

Deliver `ourdash` v0.1 per the locked SPEC: one typed Python SDK for Dash Core reads, offline payment pipeline (build → review → sign → submit → confirm), address validation, network-health reads, and Platform reads with proof verdicts — with secrets safety, typed errors, per-network endpoint discovery, quality gates, and docs that work from zero.

## Chosen Approach (Approach C — Trust-Ladder Hybrid)

- **Thin transport**: `DashRPC` / `DAPIClient` do JSON-RPC framing over HTTP with auth, timeouts, bounded retries. Transport files use stdlib + `dataclasses` only — **no pydantic import** (seam rule, enforced by `tests/test_seam.py` from Phase 1).
- **Curated pydantic facade**: user-facing typed models (`AddressInfo`, `UnsignedTx`, `IdentityInfo`, `ProofVerdict`, …) live in domain modules (`core/addresses.py`, `core/wallet.py`, `core/transactions.py`, `core/chain.py`, `platform/models.py`, `platform/drive.py`). Facade may import pydantic; transport never does.
- **Isolated proof port**: `platform/proofs.py` defines the verifier contract + `FakeVerifier` (tests) + a bridge boundary to the pinned reference verifier; greenfield pure-Python port is NOT attempted in v0.1. Explicit keyword-only `trust_node=False` fallback on every Platform read; `True` returns data labeled `UNCHECKED` plus a `UserWarning`, never silent.
- **Offline P2PKH-only signer**: `core/wallet.py` + `core/transactions.py` do BIP39 restore → BIP32/44 (coin type 5) → P2PKH build/sign fully offline. P2SH/multisig/script paths raise `PaymentError` (explicit deferral). Watch-only default; signing is an explicit, warned step.
- **Per-network seed discovery, no default URL**: the dead `https://api.dash.org` default is removed in Phase 5; `DAPIConfig.address` defaults to `None` and `DAPIClient.from_network()` resolves via `platform/seeds.py`. No hardcoded URL ever ships.
- **Import direction**: `core/` never imports from `platform/`; shared code lives in `utils/` or top-level (`errors.py`, `redact.py`).

## Phase Completion Rules

A phase is NOT complete until: (1) integration test vs its stated counterpart passes, (2) listed manual/Agent-Probe steps (if any) are performed, (3) state changes verified, (4) error paths exercised, (5) gates (`pytest`, `ruff`, `black --check`, `mypy src`) green. Status markers: ⏳ PLANNED · 🔨 CODE DONE · 🧪 TESTING · ✅ VERIFIED · 🚧 BLOCKED. Code-only completion is 🔨 CODE DONE, never ✅ VERIFIED.

## Execution Brief

- **Phase 1 — transport + safety + CI** (SPEC 2, 15-part, 17-part): error taxonomy, redaction choke point, `DashRPC` transport, regtest fixture, CI workflow, seam lint. *Test:* fake-server framing tests green; CI file exists. *Verify:* `pytest -q -m "not hybrid and not agent_probe"`, `ruff`, `black --check`, `mypy src` all green. *Done when:* remote-refused + typed-error scenarios proven.
- **Phase 2 — addresses** (SPEC 7, 8): version-byte validation (`0x4c/0x8c/0x10/0x13`), checksum, network+kind reporting. *Test:* vector suite incl. wrong-network rejection. *Done when:* vectors green, no other module touched.
- **Phase 3 — offline wallet slice + ChainLock/InstantSend reads** (SPEC 4, 5, 6, 15-part, 16-part): mnemonic restore, P2PKH-only build/review/sign/submit-refusal, per-tx finality status. *Test:* BIP39/BIP32 vectors offline; bad-submit refusal; Hybrid regtest submit+confirm. *Done when:* secrets absent from all captured outputs.
- **Phase 4 — Core reads + network health** (SPEC 1, 3, 9, 14): typed `chain.py` facade + `network.py` health (chaintips, masternode-list diff, ChainLock tip status). *Test:* fake-server + Hybrid regtest reads; analyst plain-object pulls. *Done when:* multi-wallet selection + health scenarios proven on regtest.
- **Phase 5 — Platform reads facade + proof port + FakeVerifier** (SPEC 10, 11, 12, 13): seed discovery, transport rewrite, pydantic models, proofs contract + FakeVerifier + recorded-envelope fixture. *Test:* fixture-backed verdict tests; explicit-fallback test; dead-default-absent test. *Done when:* every Platform read returns data + verdict.
- **Phase 6 — docs-from-zero + secret-scan + clean-gate** (SPEC 16, 17, 18): guides, top-level exports, README, all-context corrections, secret-scan test, fresh-checkout gate. *Test:* Agent-Probe docs walkthrough on testnet; `test_secrets.py` green; clean-checkout all-four-gates green. *Done when:* new developer completes all guides end to end.

**Expected Outcome**: pip-installable `ourdash` v0.1 with typed Core + Platform reads, safe offline payments, proof verdicts, green gates, and verified guides.

## Phase Map (Dependencies — Strictly Sequential)

| Phase | Plan file | Depends on | SPEC criteria |
|---|---|---|---|
| 1 transport + safety + CI | `phase-01-transport-safety-ci-04-09-26.md` | — (foundation) | 2, 15 (transport errors), 17 (workflow + gates) |
| 2 addresses | `phase-02-addresses-04-09-26.md` | Phase 1 (errors, redact, seam test) | 7, 8 |
| 3 offline wallet + finality reads | `phase-03-offline-wallet-04-09-26.md` | Phases 1–2 (transport, addresses, errors) | 4, 5, 6, 15 (rejected-tx), 16 (partial) |
| 4 Core reads + network health | `phase-04-core-reads-04-09-26.md` | Phases 1–3 (transport, regtest fixture) | 1, 3, 9, 14 |
| 5 Platform facade + proofs | `phase-05-platform-proofs-04-09-26.md` | Phases 1, 4 (patterns; no `core/` AND no `utils/` imports — P5 plan is stricter and wins) | 10, 11, 12, 13 |
| 6 docs + secret-scan + clean-gate | `phase-06-docs-gate-04-09-26.md` | Phases 1–5 (full public surface) | 16, 17 (clean-gate proof), 18 |

Every SPEC criterion 1–18 is covered by ≥1 phase (full map in [Full Test Matrix](#full-test-matrix)). Phase 5 MUST NOT import from `core/` or `utils/` (seam rule; the Phase 5 plan is stricter than the old wording here and wins); shared needs for Phase 5 go through `errors.py`/`redact.py` only. Other phases may share via `errors.py`/`redact.py`/`utils/`.

## Per-Phase Proof Boundaries

- **P1 green proves**: JSON-RPC framing/auth/retry behavior is correct against a fake server; every transport failure maps to a distinct typed error; non-loopback without opt-in is refused; CI workflow exists; regtest fixture boots or skips cleanly. Proves nothing about addresses, wallets, or Platform.
- **P2 green proves**: address validity + network + kind reporting is correct on fixed vectors, including wrong-network rejection. Proves nothing about keys derivation beyond first receiving address from test phrase.
- **P3 green proves**: recovery phrase → address derivation is deterministic on vectors; build/review/sign are separately observable; unsigned/malformed submits are refused pre-network; a signed regtest payment submits and its ChainLock/InstantSend confirmation state is readable. Proves nothing about Core general reads or Platform.
- **P4 green proves**: chain info / block / tx / balance / multi-wallet / chaintips / masternode-list / ChainLock-tip reads work through one typed surface on regtest; analyst pulls return plain objects. Proves nothing about Platform.
- **P5 green proves**: documents / contract / identity / DPNS / token reads return data + `ProofVerdict` on recorded fixtures; fallback requires explicit opt-in and labels `UNCHECKED`; no dead/placeholder default ships. Proves nothing about live proof crypto beyond the bridge contract (bridge target pinned + recorded in docstring).
- **P6 green proves**: a new developer completes all guides end to end (Agent-Probe); sentinels never appear in logs/errors/files; fresh-checkout install + all four gates pass.

## Shared-File Ownership Map (Disjoint — Each File Has Exactly One Writer Phase)

| File | Owner | Notes |
|---|---|---|
| `pyproject.toml` | Phase 1 | Only writer: adds `ecdsa`, `mnemonic` deps + `hybrid`/`agent_probe` markers. Later phases read only. |
| `src/ourdash/errors.py` (new) | Phase 1 | Full taxonomy upfront (incl. `DAPIError`, `ProofUnavailableError`, `PaymentError` for later phases to import). |
| `src/ourdash/redact.py` (new) | Phase 1 | Redaction choke point (banned-key set, log filter). |
| `src/ourdash/core/rpc.py` | Phase 1 | Transport rewrite (`call`, `batch`, config fields, env loader). Untouched after. |
| `tests/conftest.py` (new) | Phase 1 | Regtest `dashd` fixture (Hybrid enabler; skips without binary). |
| `tests/test_seam.py` (new) | Phase 1 | Import-direction lint (no `pydantic` string in transport files; no `platform` import in `core/`). |
| `.github/workflows/ci.yml` (new) | Phase 1 | pytest + ruff + black + mypy matrix 3.10–3.12. |
| `src/ourdash/utils/__init__.py` | Phase 2 | Hash/base58-checksum helpers. |
| `src/ourdash/core/addresses.py` | Phase 2 | Validation + network/kind facade. |
| `src/ourdash/core/wallet.py` | Phase 3 | Restore/derive/watch-only/sign (P2PKH-only). |
| `src/ourdash/core/transactions.py` | Phase 3 | Build/review/sign/submit-refusal + per-tx finality status. |
| `src/ourdash/core/chain.py` (new) | Phase 4 | Typed Core read facade. |
| `src/ourdash/core/network.py` | Phase 4 | Health reads (chaintips, masternode diff, ChainLock tip). REST/ZMQ: warnings-only, no client in v0.1. |
| `src/ourdash/platform/dapi.py` | Phase 5 | Transport rewrite (dead default removed; stays pydantic-free). |
| `src/ourdash/platform/seeds.py` (new) | Phase 5 | Per-network seeds + refresh procedure. |
| `src/ourdash/platform/models.py` (new) | Phase 5 | Pydantic facade models + `ProofVerdict`. |
| `src/ourdash/platform/proofs.py` (new) | Phase 5 | Verifier contract + `FakeVerifier` + bridge boundary. |
| `src/ourdash/platform/drive.py` | Phase 5 | Query facade (documents/identity/DPNS/tokens). |
| `tests/fixtures/platform/*` (new) | Phase 5 | Recorded proof envelopes (Hybrid enabler). |
| `src/ourdash/__init__.py` | Phase 6 | Sole writer: final top-level exports + `__all__`. Phases 1–5 use full module paths and MUST NOT touch it. |
| `README.md` | Phase 6 | Sole writer (install/layout/refs refresh). |
| `docs/*.md` (new) | Phase 6 | install, connect, first payment (testnet), first Platform read, troubleshooting. |
| `process/context/all-context.md` | Phase 6 | Plan-owned doc corrections only (DIP wording, DAPI default, Core pin, devnet port row). |
| `tests/test_secrets.py` (new) | Phase 6 | Secret-scan gate. |

Each phase's test files are owned by that phase (`test_errors.py`, `test_rpc_transport.py` → P1; `test_addresses.py` → P2; `test_wallet.py`, `test_transactions.py` → P3; `test_chain_reads.py`, `test_network.py` → P4; `test_dapi.py`, `test_proofs.py` → P5). `tests/test_import.py` is read-only for all phases (Phase 6 updates imports only if its export pass requires it — declared in the phase plan).

## Touchpoints

- Read: locked SPEC, `process/context/all-context.md`, `process/context/planning/all-planning.md`, `process/context/tests/all-tests.md`, `pyproject.toml`, `src/ourdash/**`, `tests/test_import.py`.
- Write (across program): files in the ownership map above + per-phase test files + `docs/`.
- Services: local `dashd` regtest binary (Hybrid only, never required for unit gates); testnet endpoints (Agent-Probe only).

## Public Contracts (Established Across Program — Stable After Phase 6)

- `from ourdash.core.rpc import DashRPC, DashRPCConfig` (+ `call`, `batch`, `from_env`).
- `from ourdash.errors import OurdashError, RpcError, RpcAuthError, RpcConnectionError, RpcTimeoutError, ConfigError, AddressError, WalletError, PaymentError, DAPIError, ProofError, ProofUnavailableError`.
- Address validation facade (Phase 2), wallet/tx pipeline (Phase 3), chain/network reads (Phase 4), `DAPIClient.from_network` + Drive facade + `ProofVerdict` (Phase 5), top-level re-exports (Phase 6).
- Env names only: `OURDASH_RPC_URL`, `OURDASH_RPC_USER`, `OURDASH_RPC_PASSWORD`, `OURDASH_RPC_WALLET`, `OURDASH_DAPI_ADDRESS`, `OURDASH_DAPI_TIMEOUT_S`, `OURDASH_NETWORK`.

## Blast Radius

- 7 new source modules, 5 rewritten stubs, 1 config file (single writer), 1 CI workflow, ~10 new test files, 5 new docs. No DB, no infra, no existing passing tests broken (`test_import.py` assertions preserved: version `0.1.0`, `DashRPC().config.host == "127.0.0.1"`, `DAPIClient().config.timeout_s == 30.0` — Phase 1 and Phase 5 rewrites MUST preserve these defaults).
- Risk class: medium. Mitigations: disjoint ownership, seam lint, per-phase gates, additive-only changes until Phase 6 export pass.

## Full Test Matrix

Strategy key: FA = Fully-Automated (pytest, no node) · HY = Hybrid (regtest fixture or recorded fixtures, built in P1/P5) · AP = Agent-Probe (live testnet, human/agent-run, never in CI).

| SPEC | Scenario | Phase | Strategy |
|---|---|---|---|
| 1 | local-node read (chain info, block, balance) | P4 | HY (regtest fixture) |
| 2 | remote-refused-by-default + env-only creds | P1 | FA |
| 3 | multi-wallet selection | P4 | HY (regtest fixture) |
| 4 | recovery-phrase vector → address | P3 | FA (published BIP39 vectors) |
| 5 | offline build-and-sign + bad-submit refusal | P3 | FA (vectors) |
| 6 | signed payment submits + confirms (ChainLock/InstantSend state) | P3 | HY (regtest) + AP (testnet) |
| 7 | address vectors (valid/invalid + network + kind) | P2 | FA |
| 8 | wrong-network rejection | P2 | FA |
| 9 | network health (masternode diff, chaintips, ChainLock) | P4 | HY (regtest fixture) |
| 10 | Platform read + proof verdict | P5 | HY (recorded proof fixtures) |
| 11 | explicit trusted-node fallback | P5 | FA |
| 12 | identity + username lookups | P5 | HY (recorded fixtures) + AP spot-check |
| 13 | token rules + transfers | P5 | HY (recorded fixtures) |
| 14 | analyst pulls as plain objects | P4 | AP (testnet) after HY fixtures exist |
| 15 | failure matrix (bad creds, unreachable, timeout, rejected tx) | P1 (first three) + P3 (rejected tx) | FA (fake server) |
| 16 | secret-scan over captured outputs | P6 (behavior built P1–P3) | FA |
| 17 | clean-gate (pytest + ruff + black + mypy + CI workflow exists) | P1 (workflow + green) + P6 (fresh-checkout proof) | FA |
| 18 | docs walkthrough end to end | P6 | AP (testnet) |

CI runs `pytest -q -m "not hybrid and not agent_probe"` plus `ruff check src tests`, `black --check src tests`, `mypy src` on Python 3.10–3.12.

## Rollback Notes

- Work happens on `master` (no commits yet): EXECUTE commits once per verified phase (`phase-N: <slug>`); rollback of a phase = `git revert` of that commit — safe because ownership is disjoint (no phase edits another phase's files).
- If a phase fails verification: fix forward inside that phase's files only; never borrow files from a later phase.
- Fixture captures (regtest chain, proof envelopes) are committed test data; a bad capture is rolled back by deleting the fixture files and re-running that phase's capture step.

## Phased Delivery Plan

Execute strictly in order; each phase's plan file is the authority for that phase. Entry bar for phase N+1 is phase N at ✅ VERIFIED.

1. `phase-01-transport-safety-ci-04-09-26.md` — transport, errors, redaction, regtest fixture, seam lint, CI. No dependencies.
2. `phase-02-addresses-04-09-26.md` — offline address validation. Depends on Phase 1.
3. `phase-03-offline-wallet-04-09-26.md` — wallet slice + per-tx finality. Depends on Phases 1–2.
4. `phase-04-core-reads-04-09-26.md` — Core reads + network health. Depends on Phases 1–3.
5. `phase-05-platform-proofs-04-09-26.md` — Platform facade + proof port + fixtures. Depends on Phases 1–4; no `core/` imports.
6. `phase-06-docs-gate-04-09-26.md` — exports, guides, secret-scan, clean-gate. Depends on Phases 1–5.

## Acceptance Criteria

- Every SPEC criterion 1–18 is proven per the Full Test Matrix (each criterion ≥1 phase; FA green in CI, HY green with fixtures, AP walkthroughs recorded with provenance).
- Fresh-checkout install + `pytest` + `ruff` + `black --check` + `mypy src` all green (Phase 6 clean-gate).
- Seam rule holds (`test_seam.py` green; `core/` never imports `platform/`; transport files pydantic-free).
- No dead URL ships (`api.dash.org` absent from `src/`); P2PKH-only signing fence holds; trusted-node fallback is explicit and labeled everywhere.
- Final program ✅ VERIFIED requires user confirmation of the Phase 6 docs walkthrough.

## Success Criteria

1. All 18 SPEC criteria proven per the matrix above (FA green in CI; HY green with fixtures; AP walkthroughs recorded).
2. `pytest -q -m "not hybrid and not agent_probe"`, `ruff check src tests`, `black --check src tests`, `mypy src` green on a fresh checkout (Phase 6 clean-gate).
3. Seam rule holds (`test_seam.py` green); no dead URL ships (`api.dash.org` absent from `src/`); P2PKH-only fence holds (multisig/script raises `PaymentError`).
4. Guides complete end to end on testnet by a human/agent following only the shipped docs.

## Test Infra Improvement Notes

(none identified yet — placeholder per contract; updated during coverage planning and EVL.)

## Resume and Execution Handoff

1. Selected plan: `process/general-plans/active/ourdash-sdk_04-09-26/ourdash-sdk_PLAN_04-09-26.md` (this file) + phase plans `phase-01-*.md` … `phase-06-*.md` in the same folder.
2. Last completed: none (⏳ PLANNED throughout).
3. Validate-contract status: CONDITIONAL (accepted at V5, 04-09-26) — see `## Validate Contract` below; gates Phase 1 EXECUTE.
4. Supporting context loaded: `process/context/all-context.md`, `planning/all-planning.md`, `tests/all-tests.md`, locked SPEC, `pyproject.toml`, full `src/ourdash` tree, `tests/test_import.py`, `vc-generate-plan` contract.
5. Next step: review umbrella + 6 phase plans; then say `ENTER EXECUTE MODE` to implement starting with `phase-01-transport-safety-ci-04-09-26.md`. Execute phases strictly in order 1→6; do not parallelize (each depends on the prior).
6. EXECUTE precondition (V6 P2): run `python -m venv .venv && source .venv/bin/activate && pip install -e ".[all]"` from a fresh shell before the Phase 1 gates — the `src/` layout does not collect (`ModuleNotFoundError: ourdash`) without the editable install.

## Validate Contract

Status: CONDITIONAL
Date: 04-09-26
date: 2026-09-04
generated-by: outer-pvl

Parallel strategy: sequential
Rationale: 5/7 signals (S2 public API surface, S3 4 dims + 6 sections, S4 phase program, S6 secrets/trust-boundary, S7 20+ files); EXECUTE phases strictly sequential 1→6 — each depends on the prior phase at ✅ VERIFIED. No parallelization. Model: opus for EXECUTE code-writing legs; sonnet for review/validation legs. Cost guard: not triggered.

Test gates (C3 5-column table):

| criterion id | behavior | strategy | proving test | gap-resolution |
|---|---|---|---|---|
| SPEC 2 | remote-refused-by-default + env-only creds | Fully-Automated | `pytest tests/test_errors.py tests/test_rpc_transport.py tests/test_seam.py -vv` (Phase 1, fake server, no node) | A |
| SPEC 15 (transport part) | wrong-creds / unreachable / timeout typed errors | Fully-Automated | same Phase 1 suite: 401→RpcAuthError, refused→RpcConnectionError, timeout→RpcTimeoutError | A |
| SPEC 17 (workflow part) | CI workflow exists + 4 gates green | Fully-Automated | `pytest -q -m "not hybrid and not agent_probe"` + `ruff check src tests` + `black --check src tests` + `mypy src` on 3.10–3.12 | A |
| SPEC 7 | address vectors (valid/invalid + network + kind) | Fully-Automated | `pytest tests/test_addresses.py -vv` incl. 0x4c/0x8c/0x10/0x13 constants (Phase 2) | A |
| SPEC 8 | wrong-network rejection | Fully-Automated | wrong-network matrix both directions → valid=False reason=wrong_network (Phase 2) | A |
| SPEC 4 | recovery-phrase vector → address | Fully-Automated | published BIP39 vectors offline (Phase 3) | A |
| SPEC 5 | offline build-and-sign + bad-submit refusal | Fully-Automated | build/review/sign observable steps; unsigned/malformed submit → PaymentError pre-network (Phase 3) | A |
| SPEC 15 (rejected-tx part) | rejected-tx typed error | Fully-Automated | rejected submit → PaymentError, no retry w/o fix (Phase 3) | A |
| SPEC 6 | signed payment submits + confirms (ChainLock/InstantSend) | Hybrid | regtest dashd_regtest submit+confirm (Phase 3) + Agent-Probe testnet spot-check | A (HY) + AP residual named below |
| SPEC 1 | local-node read (chain info, block, balance) | Hybrid | regtest fixture reads (Phase 4) | A |
| SPEC 3 | multi-wallet selection | Hybrid | regtest multi-wallet scenario (Phase 4) | A |
| SPEC 9 | network health (masternode diff, chaintips, ChainLock) | Hybrid | regtest fixture health reads (Phase 4) | A |
| SPEC 14 | analyst pulls as plain objects | Agent-Probe | testnet analysis-pull walkthrough after HY fixtures exist (Phase 4) | C — accepted AP-only residual (no automated gate; human/agent-run) |
| SPEC 10 | Platform read + proof verdict | Hybrid | recorded-envelope fixtures via FakeVerifier + models (Phase 5) | A |
| SPEC 11 | explicit trusted-node fallback | Fully-Automated | trust_node=True → UNCHECKED + UserWarning asserted; positional trust_node → TypeError (Phase 5) | A |
| SPEC 12 | identity + username lookups | Hybrid | recorded fixtures (Phase 5) + Agent-Probe testnet spot-check | A (HY) + AP spot-check |
| SPEC 13 | token rules + transfers | Hybrid | recorded fixtures (Phase 5) | A |
| SPEC 16 | secret-scan over captured outputs | Fully-Automated | `pytest tests/test_secrets.py -vv` sentinel scan: sentinels absent from logs/errors/files (Phase 6) | A |
| SPEC 17 (clean-gate part) | fresh-checkout install + all four gates green | Fully-Automated | venv → pip install -e ".[all]" → pytest + ruff + black --check + mypy (Phase 6) | A |
| SPEC 18 | docs walkthrough end to end | Agent-Probe | 5 guides executed verbatim on testnet by fresh reader (Phase 6) | C — accepted AP-only residual (human/agent-run, never CI) |

gap-resolution legend:
- A — proven now (gate passes in this cycle)
- B — fixed in this plan (gate added by this plan's checklist)
- C — deferred to a named later phase/plan
- D — backlog test-building stub (named residual; keep-active; continue)

C-4 reconciliation: the `strategy:` column carries ONLY the 3 proving strategies (Fully-Automated / Hybrid / Agent-Probe). Known-Gap is NEVER a `strategy:` value. Vacuous-green ban scan: no SPEC 1–18 behavior rests on Known-Gap alone — ban NOT triggered.

Legacy line form (retained so existing validate-contract consumers still parse):
- transport/errors/seam: [Fully-automated: `pytest tests/test_errors.py tests/test_rpc_transport.py tests/test_seam.py -vv`] | [hybrid: n/a] | [agent-probe: n/a] | [known-gap: none]
- core reads/health/wallet-submit: [Fully-automated: vector + fake-server suites] | [hybrid: regtest `dashd_regtest` fixture — precondition: `dashd` binary or tests skip] | [agent-probe: testnet submit + analyst-pull walkthroughs] | [known-gap: none]
- platform verdicts: [Fully-automated: dead-string + fallback-warning + FakeVerifier tests] | [hybrid: recorded proof envelopes in `tests/fixtures/platform/`] | [agent-probe: fixture-capture + identity spot-check on testnet] | [known-gap: none]
- clean-gate/secrets/docs: [Fully-automated: 4-gate fresh-checkout + sentinel scan] | [hybrid: n/a] | [agent-probe: 5-guide verbatim walkthrough] | [known-gap: none]

Failing stub (Fully-Automated rows only — execute-agent red-first starting points; Hybrid/Agent-Probe rows do NOT receive stubs):
test("should refuse remote host without remote_ok", () => { throw new Error("NOT IMPLEMENTED — TDD stub for: remote-refused-by-default + env-only creds") })
test("should map transport failures to typed errors", () => { throw new Error("NOT IMPLEMENTED — TDD stub for: wrong-creds / unreachable / timeout typed errors") })
test("should validate addresses with network and kind", () => { throw new Error("NOT IMPLEMENTED — TDD stub for: address vectors (valid/invalid + network + kind)") })
test("should reject wrong-network addresses", () => { throw new Error("NOT IMPLEMENTED — TDD stub for: wrong-network rejection") })
test("should derive address from recovery phrase", () => { throw new Error("NOT IMPLEMENTED — TDD stub for: recovery-phrase vector → address") })
test("should refuse unsigned or malformed submits", () => { throw new Error("NOT IMPLEMENTED — TDD stub for: offline build-and-sign + bad-submit refusal") })
test("should label unchecked answers only via explicit opt-in", () => { throw new Error("NOT IMPLEMENTED — TDD stub for: explicit trusted-node fallback") })
test("should keep sentinels out of logs errors and files", () => { throw new Error("NOT IMPLEMENTED — TDD stub for: secret-scan over captured outputs") })

Dimension findings:
- Infra fit: CONCERN — no containers/infra/DB/UI to conflict; regtest fixture skips cleanly without dashd; advisory: CI matrix 3.10–3.12 vs local interpreter 3.14.6 (accepted)
- Test coverage: CONCERN — SPEC 14 + SPEC 18 proven by Agent-Probe only (accepted AP-only residuals, named above); markers hybrid/agent_probe created in Phase 1 (no strict-markers, so -m selection warns-but-passes until then)
- Breaking changes: PASS — zero production callers; only consumer tests/test_import.py (2 assertions) explicitly preserved; Phase 5 DAPIConfig.address None-default flip does not touch asserted defaults
- Security surface: CONCERN — high-risk classes (secrets, trust-boundary fallback, payment signing) covered at ≥Hybrid via FA sentinel scan + HY regtest + FA redaction tests; new key-material deps (ecdsa, mnemonic) use loose >= pins (accepted for v0.1)
- Umbrella sections (Touchpoints + Ownership Map): PASS — all owner targets verified on disk; ownership disjoint across P1–P6; test_import.py read-only except P6 export assertion
- Umbrella sections (Public Contracts): CONCERN — P6 export names (Wallet/UnsignedTx/SignedTx/ConfirmationStatus) verified at EXECUTE via P6 stop-and-report rule; Phase Map P5 cell tightened by V6 P1 (no core/ AND no utils/ imports)
- Umbrella sections (Blast Radius + Rollback): PASS — revert-per-phase safe (disjoint); pre-first-commit rollback = delete files
- Umbrella sections (Test Matrix + Proof Boundaries): CONCERN — AP-only residuals named; P5 fixture-capture has synthetic-pending-recapture fallback (adequate)
- Umbrella sections (Acceptance/Success): PASS — falsifiable per-phase boundaries; fresh-checkout 4-gate green required

V3 totals: 0 FAILs / 4 CONCERNs / 6 PASSes → Net Gate CONDITIONAL.

Open gaps (accepted residuals — V5 Accept covers all):
- SPEC 14 analyst pulls: Agent-Probe only, no automated gate — accepted; human/agent-run on testnet after HY fixtures exist
- SPEC 18 docs walkthrough: Agent-Probe only, never in CI — accepted; requires user confirmation of Phase 6 walkthrough for final program ✅ VERIFIED
- CI-vs-local Python skew (3.10–3.12 vs 3.14.6): advisory only — accepted
- Loose >= pins on ecdsa/mnemonic: accepted for v0.1

V6 plan updates applied with this contract:
- P1: Phase Map P5 cell tightened to "no `core/` AND no `utils/` imports — P5 plan is stricter and wins"; §Phase Map note updated (Phase 5 shares via errors.py/redact.py only)
- P2: editable-install precondition added to §Resume and Execution Handoff (fresh venv + pip install -e ".[all]" before Phase 1 gates)

Execute-agent instructions (binding on EXECUTE):
- E1: Phase 1 EXECUTE — land `hybrid` + `agent_probe` marker registration in the same pyproject.toml edit; if `-m` selection errors pre-registration, register markers first, then re-run gates
- E2: Phase 5 EXECUTE — seeds ONLY from the two named sources (docs.dash.org Platform connectivity page + pinned proof-capable JS toolkit defaults), each entry with source URL + retrieval date; empty-list-with-reason over invented hostnames; loopback for regtest/devnet
- E3: Phase 6 EXECUTE — missing P6 export name = STOP and report back (prior phase incomplete); never invent the object in `__init__.py`

What this coverage does NOT prove:
- FA fake-server/vector suites prove framing, auth, retry, version-byte, redaction behavior — NOT live-node behavior, quorum/finality reality, or fee-market conditions
- HY regtest gates prove loopback-node behavior with a local binary — NOT testnet/mainnet behavior
- Recorded proof fixtures prove parsing + verdict plumbing — NOT live proof cryptography (bridge target pinned separately in Phase 5 docstring)
- AP walkthroughs prove human-followability once with provenance — NOT repeatability in CI
- Secret-scan proves fixed sentinels absent from captured outputs — NOT all conceivable leak shapes

EXECUTE routing: sequential 1→6. Entry bar for phase N+1 is phase N at ✅ VERIFIED. Phase 1 entry: `phase-01-transport-safety-ci-04-09-26.md` (no dependencies; foundation). Do not parallelize.

Gate: CONDITIONAL (concerns noted, user accepted)
Accepted by: user (V5 unconditional Accept, 05-09-26 session — all 4 CONCERNs + open gaps accepted as named above)

## Autonomous Goal Block

SESSION GOAL: Implement `ourdash` v0.1 per umbrella plan `process/general-plans/active/ourdash-sdk_04-09-26/ourdash-sdk_PLAN_04-09-26.md` (Approach C trust-ladder hybrid, 6 phases, SPEC 18 criteria) under CONDITIONAL validate-contract (outer-pvl, 2026-09-04; 0 FAILs, 4 accepted CONCERNs).
Autonomy rules: EXECUTE implements EXACTLY as planned starting at Phase 1; phases strictly sequential 1→6; after each phase STOP and verify before proceeding; fix forward inside owning phase files only; E1–E3 instructions binding; no scope expansion without plan amendment (gRPC streaming, multisig, X11 smuggling = pause + replan).
Hard stops: missing P6 export name = STOP + report (E3); no `core/` or `utils/` imports in Phase 5 (P1); secrets in any output = STOP + fix; test_import.py original 2 assertions must keep passing.
Next phase: Phase 1 — transport + safety + CI (`phase-01-transport-safety-ci-04-09-26.md`).
Contract summary: CONDITIONAL gate; FA+HY+AP gates per C3 table; AP-only residuals SPEC 14/18 accepted; precondition fresh venv + pip install -e ".[all]".
Execute start command: say ENTER EXECUTE MODE to implement Phase 1 per its phase plan.
Reference for latest state: process/general-plans/active/ourdash-sdk_04-09-26/ourdash-sdk_PLAN_04-09-26.md

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| Per-phase gates 1–6 (see phase plans) | FA + HY + AP per matrix | 1–18 (each criterion ≥1 phase; see matrix) |
| Fresh-checkout clean-gate (Phase 6) | FA | 17 |
| Docs walkthrough on testnet (Phase 6) | AP | 18 |
| Secret-scan (Phase 6) | FA | 16 |

## Cursor + RIPER-5 Guidance

- RIPER-5: PLAN is this artifact set; request user approval; EXECUTE implements EXACTLY as planned starting at Phase 1; after each phase STOP and verify before proceeding.
- If scope expands mid-flight (e.g. gRPC streaming, multisig signing, X11 in Python): pause, classify change, update the owning phase plan, then continue. Do not smuggle expansion into EXECUTE.
